"""
Event handler for forwarding Elite Dangerous events to VKB hardware.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .config import Config
from .rules_engine import DashboardRuleEngine, MatchResult, RuleMatchResult
from .vkb_client import VKBClient

logger = logging.getLogger(__name__)

# Pre-compiled regex for shift token parsing (optimization #11)
# Matches: Shift0-7 or Subshift0-7
_SHIFT_TOKEN_PATTERN = re.compile(r"^(Subshift|Shift)(\d+)$")


class EventHandler:
    """
    Handles EDMC events and forwards them to VKB hardware.
    
    Manages event filtering, serialization, and transmission to VKB device.
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
        self.rule_engine: Optional[DashboardRuleEngine] = None
        self._load_rules()
        self._shift_bitmap = 0
        self._subshift_bitmap = 0
        self._last_sent_shift = None
        self._last_sent_subshift = None

    def _resolve_rules_path(self) -> Path:
        override = self.config.get("rules_path", "") or ""
        if override:
            return Path(override)
        return self.plugin_dir / "rules.json"

    def _load_rules(self) -> None:
        rules_path = self._resolve_rules_path()
        if not rules_path.exists():
            logger.info(f"No rules file found at {rules_path}")
            self.rule_engine = None
            return

        try:
            with rules_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load rules from {rules_path}: {e}")
            self.rule_engine = None
            return

        rules = data.get("rules") if isinstance(data, dict) else data
        if not isinstance(rules, list):
            logger.error(f"Rules file {rules_path} must contain a list of rules")
            self.rule_engine = None
            return

        self.rule_engine = DashboardRuleEngine(rules, action_handler=self._handle_rule_action)
        logger.info(f"Loaded {len(rules)} rules from {rules_path}")

    def reload_rules(self) -> None:
        """Reload rule definitions from disk."""
        self._load_rules()

    def connect(self) -> bool:
        """
        Connect to VKB hardware and start reconnection worker.
        
        Returns:
            True if initial connection successful, False otherwise.
        """
        if self.enabled:
            success = self.vkb_client.connect()
            # Start reconnection attempts regardless of initial success
            self.vkb_client.start_reconnection()
            return success
        return False

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

        self._handle_session_events(event_type)

        # Filter by configured event types if list is not empty
        if self.event_types and event_type not in self.event_types:
            return

        if self.debug:
            logger.debug(f"Event received: {event_type}")

        # Run rule engine for all EDMC notifications.
        if self.rule_engine:
            try:
                self.rule_engine.on_notification(
                    cmdr=cmdr,
                    is_beta=is_beta,
                    source=source,
                    event_type=event_type,
                    entry=event_data,
                )
            except RuntimeError as e:
                logger.error(f"Rule engine error: {e}")
            except Exception as e:
                logger.debug(f"Unexpected error in rule engine: {e}", exc_info=True)

        # Send to VKB hardware (format is abstracted in VKBClient)
        if not self.vkb_client.send_event(event_type, event_data):
            logger.warning(f"Failed to send {event_type} event to VKB")

    def _on_socket_connected(self) -> None:
        """
        Re-apply current shift/subshift state after any socket reconnect.
        """
        self._send_shift_state_if_changed(force=True)

    def _handle_rule_action(self, result: MatchResult) -> None:
        if result.outcome == RuleMatchResult.INDETERMINATE:
            logger.debug(f"[EDMCVKBConnector:{result.rule_id}] Rule indeterminate (missing data)")
            return

        actions = result.then if result.outcome == RuleMatchResult.MATCH else result.otherwise
        if not actions:
            return

        if not isinstance(actions, dict):
            logger.warning(f"[EDMCVKBConnector:{result.rule_id}] Rule actions must be a dict")
            return

        for key, value in actions.items():
            if key == "log":
                message = str(value) if value is not None else ""
                logger.info(f"[EDMCVKBConnector:{result.rule_id}] {message}")
                continue

            if key in ("vkb_set_shift", "vkb_clear_shift"):
                if not isinstance(value, list):
                    logger.warning(f"[EDMCVKBConnector:{result.rule_id}] {key} must be a list")
                    continue
                self._apply_shift_tokens(result.rule_id, value, set_bits=(key == "vkb_set_shift"))
                continue

            logger.warning(f"[EDMCVKBConnector:{result.rule_id}] Unknown action key: {key}")

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
                logger.warning(f"[EDMCVKBConnector:{rule_id}] Invalid shift token: {token}")
                continue
            
            # Use pre-compiled regex for better performance
            match = _SHIFT_TOKEN_PATTERN.match(token)
            if not match:
                logger.warning(f"[EDMCVKBConnector:{rule_id}] Unknown shift token: {token}")
                continue
            
            shift_type = match.group(1)
            idx = int(match.group(2))
            
            # Validate index range
            if idx < 0 or idx > 7:
                logger.warning(f"[EDMCVKBConnector:{rule_id}] Shift index {idx} out of range (0-7): {token}")
                continue
            
            if shift_type == "Shift":
                self._shift_bitmap = self._apply_bit(self._shift_bitmap, idx, set_bits)
            else:  # Subshift
                self._subshift_bitmap = self._apply_bit(self._subshift_bitmap, idx, set_bits)

    def _apply_bit(self, bitmap: int, idx: int, set_bits: bool) -> int:
        mask = 1 << idx
        if set_bits:
            return bitmap | mask
        return bitmap & ~mask

    def _send_shift_state_if_changed(self, *, force: bool = False) -> None:
        payload = {
            "shift": self._shift_bitmap & 0xFF,
            "subshift": self._subshift_bitmap & 0xFF,
        }
        if force or payload["shift"] != self._last_sent_shift or payload["subshift"] != self._last_sent_subshift:
            if not self.vkb_client.send_event("VKBShiftBitmap", payload):
                logger.warning("Failed to send VKB shift/subshift bitmap")
                return
            self._last_sent_shift = payload["shift"]
            self._last_sent_subshift = payload["subshift"]

    def enable(self) -> None:
        """Enable event forwarding."""
        self.enabled = True
        logger.info("Event forwarding enabled")

    def disable(self) -> None:
        """Disable event forwarding."""
        self.enabled = False
        logger.info("Event forwarding disabled")

    def set_debug(self, enabled: bool) -> None:
        """Enable or disable debug logging."""
        self.debug = enabled
        logger.info(f"Debug logging {'enabled' if enabled else 'disabled'}")
