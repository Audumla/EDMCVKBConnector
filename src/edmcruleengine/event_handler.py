"""
Event handler for forwarding Elite Dangerous events to VKB hardware.
"""

import re
import socket
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import plugin_logger
from .config import Config
from .rule_loader import load_rules_file, RuleLoadError
from .rules_engine import RuleEngine, MatchResult
from .signals_catalog import SignalsCatalog, CatalogError
from .unregistered_events_tracker import UnregisteredEventsTracker
from .vkb_client import VKBClient
from .vkb_link_manager import VKBLinkManager

logger = plugin_logger(__name__)

# Pre-compiled regex for shift token parsing (optimization #11)
# Matches: Shift1, Shift2 or Subshift1 through Subshift8
_SHIFT_TOKEN_PATTERN = re.compile(r"^(Subshift|Shift)(\d+)$")


class EventHandler:
    """
    Handles EDMC events and forwards them to VKB hardware.

    Manages event filtering, signal derivation, rule evaluation, and
    transmission of VKBShiftBitmap packets to VKB-Link.

    Key attributes
    --------------
    track_unregistered_events : bool
        When True, events not found in the signals catalog are recorded by
        ``UnregisteredEventsTracker`` for later review.  Defaults to False.
        Toggled from the plugin preferences **Events** tab.
    """

    def __init__(
        self,
        config: Config,
        vkb_client: Optional[VKBClient] = None,
        *,
        plugin_dir: Optional[str] = None,
    ):
        """
        Initialize event handler.
        
        Args:
            config: Configuration object.
            vkb_client: VKB client instance (created if not provided).
        """
        self.config = config
        self.plugin_dir = Path(plugin_dir) if plugin_dir else Path.cwd()
        if vkb_client is None:
            self.vkb_client = VKBClient(
                host=config.get("vkb_host", "127.0.0.1"),
                port=config.get("vkb_port", 50995),
                header_byte=config.get("vkb_header_byte", 0xA5),
                command_byte=config.get("vkb_command_byte", 13),
                initial_retry_interval=config.get("initial_retry_interval", 2),
                initial_retry_duration=config.get("initial_retry_duration", 60),
                fallback_retry_interval=config.get("fallback_retry_interval", 10),
                socket_timeout=config.get("socket_timeout", 5),
                on_connected=self._on_socket_connected,
            )
        else:
            self.vkb_client = vkb_client
            self.vkb_client.set_on_connected(self._on_socket_connected)
        self.enabled = config.get("enabled", True)
        self.debug = config.get("debug", False)
        self.event_types = config.get("event_types", [])
        self.catalog: Optional[SignalsCatalog] = None
        self.rule_engine: Optional[RuleEngine] = None
        self._rules_path: Path = self._resolve_rules_path()
        self._rules_mtime_ns: Optional[int] = None
        self._load_catalog()
        self._load_rules()
        self._shift_bitmap = 0
        self._subshift_bitmap = 0
        self._last_sent_shift = None
        self._last_sent_subshift = None
        self._recent_events: Dict[str, float] = {}  # event_name -> timestamp
        self._event_window_seconds = 5  # How long to track events
        
        # Initialize unregistered events tracker
        self.unregistered_events_tracker = UnregisteredEventsTracker(
            self.plugin_dir,
            catalog=self.catalog
        )
        self._track_unregistered_events: bool = False
        self.vkb_link_manager = VKBLinkManager(config, self.plugin_dir)
        self._vkb_link_recovery_lock = threading.Lock()
        self._vkb_link_recovery_inflight = False
        self._last_vkb_link_recovery = 0.0
        self._connection_status_lock = threading.Lock()
        self._connection_status_override: Optional[str] = None
        self._endpoint_change_active = False  # Suppresses recovery during intentional restart
        self._has_successful_vkb_connection = False

    def set_connection_status_override(self, status: Optional[str]) -> None:
        """Set temporary UI-facing connection status text."""
        with self._connection_status_lock:
            self._connection_status_override = status

    def get_connection_status_override(self) -> Optional[str]:
        """Get temporary UI-facing connection status text, if any."""
        with self._connection_status_lock:
            return self._connection_status_override

    def _get_config_int(self, key: str, default: int, *, minimum: int = 0) -> int:
        value: Any = default
        if self.config:
            value = self.config.get(key)
            if value is None:
                value = default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        if parsed < minimum:
            return minimum
        return parsed

    def _get_config_float(self, key: str, default: float, *, minimum: float = 0.0) -> float:
        value: Any = default
        if self.config:
            value = self.config.get(key)
            if value is None:
                value = default
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = default
        if parsed < minimum:
            return minimum
        return parsed

    def _wait_for_vkb_listener_ready(self, host: str, port: int) -> bool:
        """Wait until VKB-Link TCP listener is reachable or timeout expires."""
        timeout_seconds = self._get_config_float(
            "vkb_link_operation_timeout_seconds",
            10.0,
            minimum=0.1,
        )
        poll_interval = self._get_config_int("vkb_link_poll_interval_ms", 250, minimum=10) / 1000.0
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                with socket.create_connection((host, int(port)), timeout=0.5):
                    logger.info(f"VKB-Link listener is ready at {host}:{port}")
                    return True
            except OSError:
                time.sleep(poll_interval)
        logger.warning(
            "Timed out waiting for VKB-Link listener readiness at "
            f"{host}:{port} (timeout={timeout_seconds:.1f}s)"
        )
        return False

    def _should_probe_listener_before_connect(self) -> bool:
        """Whether to probe the listener with a temporary socket before connect."""
        if not self.config:
            return False
        return bool(self.config.get("vkb_link_probe_listener_before_connect", False))

    def _apply_endpoint_change(self, host: str, port: int) -> None:
        """Restart VKB-Link and reconnect after host/port settings change.

        1. Suppresses recovery attempts during the intentional restart
        2. Persists endpoint settings
        3. Delegates stop/INI update/start workflow to VKBLinkManager
        4. Waits for listener readiness and reconnects
        """
        if not self.vkb_link_manager:
            logger.error("VKB-Link manager unavailable; cannot apply endpoint change")
            self.set_connection_status_override(None)
            return

        self._endpoint_change_active = True
        try:
            logger.info(f"VKB-Link: applying endpoint change (host={host} port={port})")
            self.set_connection_status_override("Restarting VKB-Link...")

            # Persist the new endpoint to config so future connects use the right address
            if self.config:
                self.config.set("vkb_host", host)
                self.config.set("vkb_port", port)

            # Directly update vkb_client endpoint (config may not be saved by user yet)
            logger.info(f"VKB-Link: updating connection endpoint to {host}:{port}")
            self.vkb_client.host = host
            self.vkb_client.port = port

            result = self.vkb_link_manager.apply_managed_endpoint_change(
                host=host,
                port=port,
                reason="endpoint_change",
            )
            logger.info(f"VKB-Link endpoint-change result: {result.message}")
            if not result.success:
                logger.error("VKB-Link: managed endpoint change failed")
                return

            if self._should_probe_listener_before_connect():
                self._wait_for_vkb_listener_ready(host, port)
            logger.info(f"VKB-Link: connecting to {host}:{port}")
            self.set_connection_status_override("Connecting to VKB-Link...")
            self.vkb_client.set_on_connected(self._on_socket_connected)
            if self.vkb_client.connect():
                logger.info(f"VKB-Link: connected to {host}:{port}")
            else:
                logger.warning(f"VKB-Link: connect to {host}:{port} failed; reconnect worker will retry")
        except Exception as e:
            logger.error(f"VKB-Link: endpoint change failed: {e}")
        finally:
            self._endpoint_change_active = False
            self.set_connection_status_override(None)

    @property
    def track_unregistered_events(self) -> bool:
        """Whether unregistered event tracking is enabled."""
        return self._track_unregistered_events

    @track_unregistered_events.setter
    def track_unregistered_events(self, value: bool) -> None:
        self._track_unregistered_events = bool(value)

    def _resolve_rules_path(self) -> Path:
        override = self.config.get("rules_path", "") or ""
        if override:
            return Path(override)
        return self.plugin_dir / "rules.json"

    def _load_catalog(self) -> None:
        """Load signals catalog from plugin directory."""
        try:
            self.catalog = SignalsCatalog.from_plugin_dir(str(self.plugin_dir))
            logger.info("Loaded signals catalog")
            # Update tracker's catalog reference if tracker exists
            if hasattr(self, 'unregistered_events_tracker'):
                self.unregistered_events_tracker.set_catalog(self.catalog)
        except CatalogError as e:
            logger.error(f"Failed to load signals catalog: {e}")
            self.catalog = None
        except Exception as e:
            logger.error(f"Unexpected error loading catalog: {e}")
            self.catalog = None

    def _load_rules(self, *, preserve_on_error: bool = False) -> None:
        rules_path = self._resolve_rules_path()
        self._rules_path = rules_path

        # Catalog is required for rules
        if self.catalog is None:
            logger.error("Cannot load rules: signals catalog not loaded")
            self.rule_engine = None
            return

        if not rules_path.exists():
            logger.info(f"No rules file found at {rules_path}")
            self.rule_engine = None
            self._rules_mtime_ns = None
            return

        try:
            mtime_ns = rules_path.stat().st_mtime_ns
        except OSError:
            mtime_ns = None

        try:
            rules = load_rules_file(rules_path)
        except RuleLoadError as e:
            if preserve_on_error and self.rule_engine is not None:
                logger.warning(f"Failed to reload rules from {rules_path}: {e}; keeping previous rules")
                return
            logger.error(f"Failed to load rules from {rules_path}: {e}")
            self.rule_engine = None
            return
        except Exception as e:
            if preserve_on_error and self.rule_engine is not None:
                logger.warning(f"Unexpected error reloading rules: {e}; keeping previous rules")
                return
            logger.error(f"Unexpected error loading rules: {e}")
            self.rule_engine = None
            return

        self.rule_engine = RuleEngine(rules, self.catalog, action_handler=self._handle_rule_action)
        self._rules_mtime_ns = mtime_ns
        logger.info(f"Loaded {len(rules)} rules from {rules_path}")

    def _reload_rules_if_changed(self) -> None:
        current_path = self._resolve_rules_path()
        current_mtime_ns: Optional[int] = None

        if current_path.exists():
            try:
                current_mtime_ns = current_path.stat().st_mtime_ns
            except OSError:
                current_mtime_ns = None

        if current_path != self._rules_path or current_mtime_ns != self._rules_mtime_ns:
            logger.info(f"Detected rules file change, reloading: {current_path}")
            self._load_rules(preserve_on_error=True)

    def reload_rules(self) -> None:
        """Reload rule definitions from disk."""
        self._load_rules()

    def connect(self) -> bool:
        """
        Connect to VKB hardware and start reconnection worker.
        
        Returns:
            True if initial connection successful, False otherwise.
        """
        if not self.enabled:
            return False
        self.set_connection_status_override("Connecting to VKB-Link...")
        try:
            host = self.config.get("vkb_host", "127.0.0.1")
            port = self.config.get("vkb_port", 50995)
            self.vkb_client.host = host
            self.vkb_client.port = port

            # Connection workflow requires VL process running first.
            if self.vkb_link_manager:
                status = self.vkb_link_manager.get_status(check_running=True)
                auto_manage = bool(self.config.get("vkb_link_auto_manage", True)) if self.config else True
                if status.running is False:
                    if not auto_manage and not status.exe_path:
                        logger.warning(
                            "VKB-Link connect aborted: process is not running and auto-manage is disabled"
                        )
                        return False
                    ensure_result = self.vkb_link_manager.ensure_running(
                        host=host,
                        port=port,
                        reason="connect",
                    )
                    logger.info(f"VKB-Link ensure-before-connect result: {ensure_result.message}")
                    if not ensure_result.success:
                        return False
                self.vkb_link_manager.wait_for_post_start_settle()
                if self._should_probe_listener_before_connect():
                    self._wait_for_vkb_listener_ready(host, port)

            # Ensure reconnect callbacks always re-send shift state on new socket connections.
            self.vkb_client.set_on_connected(self._on_socket_connected)
            success = self.vkb_client.connect()
            # Start reconnection attempts regardless of initial success
            self.vkb_client.start_reconnection()
            if not success:
                self._attempt_vkb_link_recovery(reason="connect_failed")
            return success
        finally:
            self.set_connection_status_override(None)

    def _refresh_vkb_endpoint(self) -> None:
        """
        Refresh VKB client endpoint from current config.
        
        Called when preferences change to ensure reconnect targets
        the new host/port instead of cached values.
        """
        vkb_host = self.config.get("vkb_host", "127.0.0.1")
        vkb_port = self.config.get("vkb_port", 50995)
        
        # Update VKB client endpoint if changed
        if self.vkb_client.host != vkb_host or self.vkb_client.port != vkb_port:
            logger.info(
                f"Updating VKB endpoint from {self.vkb_client.host}:{self.vkb_client.port} "
                f"to {vkb_host}:{vkb_port}"
            )
            self.vkb_client.host = vkb_host
            self.vkb_client.port = vkb_port

    def disconnect(self) -> None:
        """Disconnect from VKB hardware."""
        self.vkb_client.disconnect()

    def clear_shift_state_for_shutdown(self) -> bool:
        """Send a zero shift/subshift state before shutdown without recovery side effects."""
        self._shift_bitmap = 0
        self._subshift_bitmap = 0
        sent = self._send_shift_state_if_changed(force=True, allow_recovery=False)
        if sent:
            logger.info("VKB-Link shutdown clear state sent")
        else:
            logger.warning("VKB-Link shutdown clear state send failed")
        return sent

    def handle_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        *,
        source: str = "journal",
        cmdr: str = "",
        is_beta: bool = False,
    ) -> None:
        """
        Handle an EDMC event.
        
        Args:
            event_type: Type of event (e.g., "Location", "FSDJump").
            event_data: Event data dictionary.
        """
        if not self.enabled:
            return

        self._reload_rules_if_changed()

        self._handle_session_events(event_type)

        # Filter by configured event types if list is not empty
        if self.event_types and event_type not in self.event_types:
            return

        if self.debug:
            logger.debug(f"Event received: {event_type}")

        # Track journal events with timestamps for recent operator
        if source == "journal":
            current_time = time.time()
            self._recent_events[event_type] = current_time
            # Prune events older than the tracking window
            cutoff = current_time - self._event_window_seconds
            self._recent_events = {
                k: v for k, v in self._recent_events.items() if v >= cutoff
            }

        # Run rule engine for all EDMC notifications.
        # Only rule actions (vkb_set_shift / vkb_clear_shift) trigger VKB sends.
        # Raw events are NOT forwarded to VKB-Link because the device only
        # understands VKBShiftBitmap packets — sending arbitrary text would
        # violate the protocol.
        if self.rule_engine:
            try:
                # Pass context including recent events
                context = {
                    "recent_events": self._recent_events.copy(),
                    "trigger_source": source,
                    "event_name": event_type,
                }
                
                self.rule_engine.on_notification(
                    cmdr=cmdr,
                    is_beta=is_beta,
                    source=source,
                    event_type=event_type,
                    entry=event_data,
                    context=context,
                )
            except RuntimeError as e:
                logger.error(f"Rule engine error: {e}")
            except Exception as e:
                logger.debug(f"Unexpected error in rule engine: {e}", exc_info=True)
        else:
            logger.debug(f"No rule engine loaded — event '{event_type}' not forwarded to VKB")
        
        # Track unregistered events (events not found in the signals catalog)
        # This helps identify missing events that should be added to the catalog
        if self._track_unregistered_events:
            try:
                self.unregistered_events_tracker.track_event(event_type, event_data, source=source)
            except Exception as e:
                logger.debug(f"Error tracking unregistered event: {e}", exc_info=True)

    def _on_socket_connected(self) -> None:
        """
        Re-apply current shift/subshift state after any socket reconnect.
        """
        self._has_successful_vkb_connection = True
        logger.info(
            "VKB socket connected; resending current shift state "
            f"(shift=0x{self._shift_bitmap & 0x03:02x} subshift=0x{self._subshift_bitmap & 0x7f:02x})"
        )
        if not self._send_shift_state_if_changed(force=True):
            logger.warning("Failed to resend shift/subshift state after socket connection")

    def _handle_rule_action(self, result: MatchResult) -> None:
        """
        Handle rule match result.
        
        Rules use edge-triggering, so this is only called when actions
        should be executed (on state transitions).
        """
        actions_list = result.actions_to_execute
        if not actions_list:
            return

        for action in actions_list:
            if not isinstance(action, dict):
                logger.warning(f"[{result.rule_id}] Action must be a dict, got {type(action)}")
                continue

            for key, value in action.items():
                if key == "log":
                    message = str(value) if value is not None else ""
                    logger.info(f"[{result.rule_title}] {message}")
                    continue

                if key in ("vkb_set_shift", "vkb_clear_shift"):
                    if not isinstance(value, list):
                        logger.warning(f"[{result.rule_id}] {key} must be a list")
                        continue
                    self._apply_shift_tokens(result.rule_id, value, set_bits=(key == "vkb_set_shift"))
                    continue

                logger.warning(f"[{result.rule_id}] Unknown action key: {key}")

        self._send_shift_state_if_changed()

    def _handle_session_events(self, event_type: str) -> None:
        if event_type in ("Commander", "LoadGame", "Shutdown"):
            self._reset_shift_state()

    def _reset_shift_state(self) -> None:
        self._shift_bitmap = 0
        self._subshift_bitmap = 0
        self._send_shift_state_if_changed(force=True)

    def _apply_shift_tokens(self, rule_id: str, tokens: list, *, set_bits: bool) -> None:
        for token in tokens:
            if not isinstance(token, str):
                logger.warning(f"[{rule_id}] Invalid shift token: {token}")
                continue
            
            # Use pre-compiled regex for better performance
            match = _SHIFT_TOKEN_PATTERN.match(token)
            if not match:
                logger.warning(f"[{rule_id}] Unknown shift token: {token}")
                continue
            
            shift_type = match.group(1)
            idx = int(match.group(2))
            
            if shift_type == "Shift":
                # Shift codes 1-2 (Shift1 maps to bit 0, Shift2 to bit 1)
                if idx < 1 or idx > 2:
                    logger.warning(f"[{rule_id}] Shift index {idx} out of range (1-2): {token}")
                    continue
                self._shift_bitmap = self._apply_bit(self._shift_bitmap, idx-1, set_bits)
            else:  # Subshift
                # Subshift codes 1-8 (Subshift1 maps to bit 0, Subshift8 to bit 7)
                if idx < 1 or idx > 8:
                    logger.warning(f"[{rule_id}] Subshift index {idx} out of range (1-8): {token}")
                    continue
                bit_pos = idx - 1
                self._subshift_bitmap = self._apply_bit(self._subshift_bitmap, bit_pos, set_bits)

    def _apply_bit(self, bitmap: int, idx: int, set_bits: bool) -> int:
        mask = 1 << idx
        if set_bits:
            return bitmap | mask
        return bitmap & ~mask

    def _send_shift_state_if_changed(self, *, force: bool = False, allow_recovery: bool = True) -> bool:
        payload = {
            "shift": self._shift_bitmap & 0x03,      # Shift1/Shift2 only (bits 0-1)
            "subshift": self._subshift_bitmap & 0x7F,  # 7 subshift codes (bits 0-6)
        }
        if force or payload["shift"] != self._last_sent_shift or payload["subshift"] != self._last_sent_subshift:
            if not self.vkb_client.send_event("VKBShiftBitmap", payload):
                logger.warning("Failed to send VKB shift/subshift bitmap")
                if allow_recovery:
                    self._attempt_vkb_link_recovery(reason="send_failed")
                return False
            self._last_sent_shift = payload["shift"]
            self._last_sent_subshift = payload["subshift"]
            active_shifts = [
                shift_num
                for shift_num, bit_pos in ((1, 0), (2, 1))
                if payload["shift"] & (1 << bit_pos)
            ]
            active_subshifts = [i + 1 for i in range(7) if payload["subshift"] & (1 << i)]
            logger.info(f"VKB-Link <- Shift {active_shifts} Subshift {active_subshifts}")
        return True

    # ==== Unregistered Events Management ====
    
    def get_unregistered_events(self) -> List[Dict[str, Any]]:
        """
        Get list of all tracked unregistered events.
        
        Returns:
            List of event entry dictionaries, sorted by last_seen (newest first)
        """
        return self.unregistered_events_tracker.get_unregistered_events()
    
    def get_unregistered_events_count(self) -> int:
        """Get the count of tracked unregistered events."""
        return self.unregistered_events_tracker.get_events_count()
    
    def refresh_unregistered_events_against_catalog(self) -> int:
        """
        Refresh unregistered events list against the current catalog.
        
        Removes any events that are now found in the catalog.
        
        Returns:
            Number of events removed from the tracking list
        """
        return self.unregistered_events_tracker.refresh_against_catalog()
    
    def clear_unregistered_event(self, event_type: str) -> bool:
        """
        Clear a specific unregistered event from tracking.
        
        Args:
            event_type: Event type to clear
            
        Returns:
            True if cleared, False if not found
        """
        return self.unregistered_events_tracker.clear_event(event_type)
    
    def clear_all_unregistered_events(self) -> int:
        """
        Clear all tracked unregistered events.
        
        Returns:
            Number of events cleared
        """
        return self.unregistered_events_tracker.clear_all_events()

    def _attempt_vkb_link_recovery(self, *, reason: str) -> None:
        """Attempt to recover VKB-Link process/INI when connection fails."""
        if not self.config or not self.vkb_link_manager:
            return
        if not bool(self.config.get("vkb_link_auto_manage", True)):
            return
        if reason == "send_failed" and not self._has_successful_vkb_connection:
            logger.info(
                "VKB-Link recovery suppressed for send_failed before first successful VKB connection"
            )
            return
        # Skip recovery if an intentional endpoint change is already in progress
        if self._endpoint_change_active:
            logger.debug("VKB-Link recovery suppressed: endpoint change in progress")
            return

        cooldown = int(self.config.get("vkb_link_recovery_cooldown", 60) or 60)
        now = time.time()
        if now - self._last_vkb_link_recovery < cooldown:
            return

        with self._vkb_link_recovery_lock:
            if self._vkb_link_recovery_inflight:
                return
            self._vkb_link_recovery_inflight = True
            self._last_vkb_link_recovery = now

        host = self.config.get("vkb_host", "127.0.0.1")
        port = self.config.get("vkb_port", 50995)

        def _worker() -> None:
            try:
                self.set_connection_status_override("Recovering VKB-Link...")
                result = self.vkb_link_manager.ensure_running(host=host, port=port, reason=reason)
                logger.info(f"VKB-Link recovery result: {result.message}")
                if result.success:
                    self.vkb_link_manager.wait_for_post_start_settle()
                    if self._should_probe_listener_before_connect():
                        self._wait_for_vkb_listener_ready(host, port)
                    self.set_connection_status_override("Connecting to VKB-Link...")
                    self.vkb_client.set_on_connected(self._on_socket_connected)
                    reconnected = self.vkb_client.connect()
                    if reconnected:
                        logger.info("VKB-Link recovery reconnect succeeded")
                    else:
                        logger.warning("VKB-Link recovery reconnect attempt failed")
            except Exception as e:
                logger.error(f"VKB-Link recovery error: {e}")
            finally:
                self.set_connection_status_override(None)
                with self._vkb_link_recovery_lock:
                    self._vkb_link_recovery_inflight = False

        threading.Thread(target=_worker, daemon=True).start()
