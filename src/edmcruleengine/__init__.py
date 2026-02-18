"""
EDMC VKB Connector - Forward Elite Dangerous events to VKB hardware.

This extension forwards game events from EDMC to VKB hardware via TCP/IP socket connection.
The VKB-Link packet format used by the plugin is implemented in
`VKBLinkMessageFormatter` (`VKBShiftBitmap` packets).
"""

import logging
import sys

from .version import __version__

__author__ = "EDMC VKB Connector Contributors"
__license__ = "MIT"

# Central logger name for the plugin.  load.py sets this to
# "EDMarketConnector.<folder>" at EDMC startup so every submodule
# logs under the same hierarchy that EDMC manages.  During tests
# (where load.py is never imported) the default "edmcruleengine"
# parent is used, which pytest's log_cli captures automatically.
_PLUGIN_LOGGER_NAME: str = "edmcruleengine"


def set_plugin_logger_name(name: str) -> None:
    """Override the plugin logger name (called by load.py at EDMC startup)."""
    global _PLUGIN_LOGGER_NAME
    _PLUGIN_LOGGER_NAME = name

    # Rebind module-level logger objects in already-imported submodules.
    # This matters in EDMC because load.py imports set_plugin_logger_name
    # from this package before plugin_start3 runs, which imports submodules
    # that create logger globals immediately.
    _submodule_names = (
        "config", "vkb_client", "event_handler",
        "rules_engine", "unregistered_events_tracker",
    )
    for suffix in _submodule_names:
        for prefix in ("edmcruleengine", "src.edmcruleengine"):
            module_name = f"{prefix}.{suffix}"
            module = sys.modules.get(module_name)
            if module is not None and hasattr(module, "logger"):
                module.logger = plugin_logger(module.__name__)
                break  # only rebind once per submodule


def _apply_edmc_context_filter(log: logging.Logger) -> None:
    """Attach EDMCContextFilter to *log* if available and not already present.

    EDMCContextFilter adds ``osthreadid`` and ``qualname`` fields that EDMC's
    log formatter expects.  EDMC only attaches it to the top-level plugin
    logger returned by ``get_plugin_logger()``, but Python's propagation model
    means it never runs for records emitted by *child* loggers.  We therefore
    attach it directly to each child logger so every record is stamped before
    reaching the EDMC file handler.
    """
    try:
        from EDMCLogging import EDMCContextFilter  # type: ignore
        # Avoid adding duplicate filters on repeated calls (e.g. logger rebind).
        if not any(isinstance(f, EDMCContextFilter) for f in log.filters):
            log.addFilter(EDMCContextFilter())
    except Exception:
        pass  # Not running inside EDMC – no-op.


def plugin_logger(module: str) -> logging.Logger:
    """Return a child logger under the plugin hierarchy.

    Usage in submodules::

        from edmcruleengine import plugin_logger
        logger = plugin_logger(__name__)

    Inside EDMC this yields e.g. ``EDMarketConnector.edmcruleengine.config``.
    During tests it yields ``edmcruleengine.config``.
    """
    # Derive a child name by stripping any package prefix and appending to
    # the managed root so EDMC context filters are inherited.
    # e.g. module="edmcruleengine.config" -> child="EDMarketConnector.<folder>.config"
    base = _PLUGIN_LOGGER_NAME
    # Strip known package prefixes so we get just the leaf module name
    for pkg in ("src.edmcruleengine.", "edmcruleengine."):
        if module.startswith(pkg):
            leaf = module[len(pkg):]
            log = logging.getLogger(f"{base}.{leaf}")
            _apply_edmc_context_filter(log)
            return log
    # Caller is the root package itself or an unknown path
    log = logging.getLogger(base)
    _apply_edmc_context_filter(log)
    return log

from .vkb_client import VKBClient
from .event_handler import EventHandler
from .config import Config
from .message_formatter import MessageFormatter, VKBLinkMessageFormatter

__all__ = [
    "VKBClient",
    "EventHandler",
    "Config",
    "MessageFormatter",
    "VKBLinkMessageFormatter",
]

