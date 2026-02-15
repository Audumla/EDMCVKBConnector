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
    for module_name in (
        "src.edmcruleengine.config",
        "src.edmcruleengine.vkb_client",
        "src.edmcruleengine.event_handler",
        "src.edmcruleengine.rules_engine",
        "edmcruleengine.config",
        "edmcruleengine.vkb_client",
        "edmcruleengine.event_handler",
        "edmcruleengine.rules_engine",
    ):
        module = sys.modules.get(module_name)
        if module is None or not hasattr(module, "logger"):
            continue
        module.logger = plugin_logger(module.__name__)


def plugin_logger(module: str) -> logging.Logger:
    """Return a child logger under the plugin hierarchy.

    Usage in submodules::

        from edmcruleengine import plugin_logger
        logger = plugin_logger(__name__)

    Inside EDMC this yields e.g. ``EDMarketConnector.edmcruleengine.config``.
    During tests it yields ``edmcruleengine.config``.
    """
    # Always return the base plugin logger.
    # In EDMC this logger has EDMCContextFilter attached by
    # EDMCLogging.get_plugin_logger(), which adds fields like
    # osthreadid/qualname used by EDMC's log formatter.
    return logging.getLogger(_PLUGIN_LOGGER_NAME)

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

