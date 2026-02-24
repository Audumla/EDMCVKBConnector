"""
Generic event handler for forwarding Elite Dangerous events to configurable endpoints.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .. import plugin_logger
from ..rules.rule_loader import load_rules_file, RuleLoadError
from ..rules.rules_engine import RuleEngine, MatchResult
from ..rules.signals_catalog import SignalsCatalog, CatalogError
from .unregistered_events_tracker import UnregisteredEventsTracker

if TYPE_CHECKING:
    from ..config.config import Config
    from .endpoint import Endpoint

logger = plugin_logger(__name__)


class EventHandler:
    """
    Naive event handler that processes EDMC events and notifies registered endpoints.

    Manages event filtering, signal derivation, and rule evaluation.
    Delegates all hardware or external interaction to a list of registered Endpoints.
    """

    def __init__(
        self,
        config: Config,
        endpoints: Optional[List[Endpoint]] = None,
        *,
        plugin_dir: Optional[str] = None,
    ):
        """
        Initialize event handler.

        Args:
            config: Configuration object.
            endpoints: Initial list of rule action endpoints.
            plugin_dir: Root directory of the plugin.
        """
        self.config = config
        self.plugin_dir = Path(plugin_dir) if plugin_dir else Path.cwd()
        self.endpoints = endpoints if endpoints is not None else []
        
        # Auto-register VKBLinkManager if none provided and config has vkb_host
        # This keeps the handler "naive" in logic but "ready-to-use" in practice.
        if endpoints is None:
            from ..vkb.vkb_client import VKBClient
            from ..vkb.vkb_link_manager import VKBLinkManager
            
            vkb_client = VKBClient(
                host=config.get("vkb_host", "127.0.0.1"),
                port=config.get("vkb_port", 50995),
                header_byte=config.get("vkb_header_byte", 0xA5),
                command_byte=config.get("vkb_command_byte", 13),
                socket_timeout=config.get("socket_timeout", 5),
            )
            vkb_manager = VKBLinkManager(config, self.plugin_dir, client=vkb_client)
            self.endpoints.append(vkb_manager)
        
        self.enabled = config.get("enabled", True)
        self.debug = config.get("debug", False)
        self.event_types = config.get("event_types", [])
        
        self.catalog: Optional[SignalsCatalog] = None
        self.rule_engine: Optional[RuleEngine] = None
        self._rules_path: Path = self._resolve_rules_path()
        self._rules_mtime_ns: Optional[int] = None
        
        self._recent_events: Dict[str, float] = {}  # event_name -> timestamp
        self._event_window_seconds = 5  # How long to track events

        self._load_catalog()
        self._load_rules()

        # Initialize unregistered events tracker
        self.unregistered_events_tracker = UnregisteredEventsTracker(
            self.plugin_dir,
            catalog=self.catalog
        )
        self.track_unregistered_events = config.get("track_unregistered_events", False)

    @property
    def track_unregistered_events(self) -> bool:
        """Whether unregistered event tracking is enabled."""
        return self._track_unregistered_events

    @track_unregistered_events.setter
    def track_unregistered_events(self, value: bool) -> None:
        self._track_unregistered_events = bool(value)

        # Initialize event anonymizer
        from .event_anonymizer import EventAnonymizer
        self.anonymizer = EventAnonymizer(
            mock_commander_name=self.config.get("mock_commander_name", "TestCommander"),
            mock_ship_name=self.config.get("mock_ship_name", "TestShip"),
            mock_ship_ident=self.config.get("mock_ship_ident", "TEST-01"),
        )

    @property
    def vkb_client(self) -> Any:
        """Compatibility property to access the VKB client from the registered manager."""
        # Try to find VKBLinkManager in endpoints
        from ..vkb.vkb_link_manager import VKBLinkManager
        for endpoint in self.endpoints:
            if isinstance(endpoint, VKBLinkManager):
                return endpoint.client
        return None

    @property
    def vkb_link_manager(self) -> Any:
        """Compatibility property to access the VKB manager from the registered endpoints."""
        from ..vkb.vkb_link_manager import VKBLinkManager
        for endpoint in self.endpoints:
            if isinstance(endpoint, VKBLinkManager):
                return endpoint
        return None

    def add_endpoint(self, endpoint: Endpoint) -> None:
        """Register a new rule action endpoint."""
        if endpoint not in self.endpoints:
            self.endpoints.append(endpoint)
            logger.info(f"Registered endpoint: {endpoint.name}")

    def connect(self) -> bool:
        """Initialize all registered endpoints."""
        if not self.enabled:
            return False
        
        success = True
        for endpoint in self.endpoints:
            try:
                if not endpoint.connect():
                    logger.warning(f"Endpoint '{endpoint.name}' failed to connect")
                    success = False
            except Exception as e:
                logger.error(f"Error connecting endpoint '{endpoint.name}': {e}", exc_info=True)
                success = False
        return success

    def disconnect(self) -> None:
        """Disconnect all registered endpoints."""
        for endpoint in self.endpoints:
            try:
                endpoint.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting endpoint '{endpoint.name}': {e}", exc_info=True)

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
        Handle an EDMC event and evaluate rules.
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
            cutoff = current_time - self._event_window_seconds
            self._recent_events = {
                k: v for k, v in self._recent_events.items() if v >= cutoff
            }

        # Run rule engine
        if self.rule_engine:
            try:
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
            except Exception as e:
                logger.debug(f"Error in rule engine: {e}", exc_info=True)

        # Track unregistered events
        if self._track_unregistered_events:
            try:
                self.unregistered_events_tracker.track_event(event_type, event_data, source=source)
            except Exception as e:
                logger.debug(f"Error tracking unregistered event: {e}", exc_info=True)

    def _handle_rule_action(self, result: MatchResult) -> None:
        """
        Relay rule match actions to endpoints.
        """
        actions_list = result.actions_to_execute
        if not actions_list:
            return

        for action in actions_list:
            if not isinstance(action, dict):
                continue

            for key, value in action.items():
                if key == "log":
                    message = str(value) if value is not None else ""
                    logger.info(f"[{result.rule_title}] {message}")
                    continue

                # Delegate to endpoints
                handled = False
                for endpoint in self.endpoints:
                    try:
                        if endpoint.handle_action(key, value, result):
                            handled = True
                            break
                    except Exception as e:
                        logger.error(f"Error in endpoint '{endpoint.name}' action handler: {e}")
                
                if not handled and key != "log":
                    logger.debug(f"Action key '{key}' was not handled by any endpoint")

    def _handle_session_events(self, event_type: str) -> None:
        """Notify endpoints of session-level lifecycle events."""
        if event_type in ("Commander", "LoadGame", "Shutdown"):
            for endpoint in self.endpoints:
                try:
                    endpoint.on_session_event(event_type)
                except Exception as e:
                    logger.error(f"Error in endpoint '{endpoint.name}' session handler: {e}")

    # --- Internal Helpers ---

    def _resolve_rules_path(self) -> Path:
        override = self.config.get("rules_path", "") or ""
        if override:
            return Path(override)
        return self.plugin_dir / "rules.json"

    def _load_catalog(self) -> None:
        try:
            self.catalog = SignalsCatalog.from_plugin_dir(str(self.plugin_dir))
            logger.info("Loaded signals catalog")
            if hasattr(self, 'unregistered_events_tracker'):
                self.unregistered_events_tracker.set_catalog(self.catalog)
        except Exception as e:
            logger.error(f"Failed to load signals catalog: {e}")
            self.catalog = None

    def _load_rules(self, *, preserve_on_error: bool = False) -> None:
        rules_path = self._resolve_rules_path()
        self._rules_path = rules_path

        if self.catalog is None:
            if not preserve_on_error:
                self.rule_engine = None
            return

        if not rules_path.exists():
            if not preserve_on_error:
                self.rule_engine = None
                self._rules_mtime_ns = None
            return

        try:
            mtime_ns = rules_path.stat().st_mtime_ns
            rules = load_rules_file(rules_path)
            self.rule_engine = RuleEngine(rules, self.catalog, action_handler=self._handle_rule_action)
            self._rules_mtime_ns = mtime_ns
            logger.info(f"Loaded {len(rules)} rules from {rules_path}")
        except Exception as e:
            if not preserve_on_error:
                self.rule_engine = None
            logger.error(f"Failed to load rules: {e}")

    def _reload_rules_if_changed(self) -> None:
        current_path = self._resolve_rules_path()
        current_mtime_ns = current_path.stat().st_mtime_ns if current_path.exists() else None

        if current_path != self._rules_path or current_mtime_ns != self._rules_mtime_ns:
            self._load_rules(preserve_on_error=True)

    # ==== Unregistered Events Management ====

    def get_unregistered_events(self) -> List[Dict[str, Any]]:
        return self.unregistered_events_tracker.get_unregistered_events()

    def get_unregistered_events_count(self) -> int:
        return self.unregistered_events_tracker.get_events_count()

    def refresh_unregistered_events_against_catalog(self) -> int:
        return self.unregistered_events_tracker.refresh_against_catalog()

    def clear_unregistered_event(self, event_type: str) -> bool:
        return self.unregistered_events_tracker.clear_event(event_type)

    def clear_all_unregistered_events(self) -> int:
        return self.unregistered_events_tracker.clear_all_events()

    # --- Compatibility Proxy Methods (Delegates to VKBLinkManager endpoint) ---

    def set_connection_status_override(self, status: Optional[str]) -> None:
        """Compatibility proxy for UI status messages."""
        manager = self.vkb_link_manager
        if manager:
            manager.set_connection_status_override(status)

    def get_connection_status_override(self) -> Optional[str]:
        """Compatibility proxy for UI status messages."""
        manager = self.vkb_link_manager
        return manager.get_connection_status_override() if manager else None

    def _apply_endpoint_change(self, host: str, port: int) -> None:
        """Compatibility proxy for endpoint updates."""
        manager = self.vkb_link_manager
        if manager:
            manager.apply_managed_endpoint_change(host=host, port=port)

    def _on_vkb_link_process_crash(self) -> None:
        """Compatibility proxy for process recovery."""
        manager = self.vkb_link_manager
        if manager:
            manager._attempt_recovery(
                reason="process_crash_detected",
                on_connected_callback=self._on_socket_connected
            )

    def _on_socket_connected(self) -> None:
        """Callback for VKB client when socket connects."""
        manager = self.vkb_link_manager
        if manager:
            manager._on_socket_connected()

    def clear_shift_state_for_shutdown(self) -> bool:
        """Compatibility proxy for shutdown cleanup."""
        manager = self.vkb_link_manager
        if manager:
            # Shift state reset is handled by on_session_event("Shutdown")
            manager.on_session_event("Shutdown")
            return True
        return False
