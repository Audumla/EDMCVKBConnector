"""
EDMC VKB Connector - Forward Elite Dangerous events to VKB hardware.

This extension forwards game events from EDMC to VKB hardware via TCP/IP socket connection.
The message format is abstracted and can be customized via MessageFormatter subclasses.
"""

import logging
import sys

__version__ = "0.1.0"
__author__ = "EDMC VKB Connector Contributors"
__license__ = "MIT"

# Central logger name for the plugin.  load.py sets this to
# "EDMarketConnector.<folder>" at EDMC startup so every submodule
# logs under the same hierarchy that EDMC manages.  During tests
# (where load.py is never imported) the default "edmcvkbconnector"
# parent is used, which pytest's log_cli captures automatically.
_PLUGIN_LOGGER_NAME: str = "edmcvkbconnector"


def set_plugin_logger_name(name: str) -> None:
    """Override the plugin logger name (called by load.py at EDMC startup)."""
    global _PLUGIN_LOGGER_NAME
    _PLUGIN_LOGGER_NAME = name

    # Rebind module-level logger objects in already-imported submodules.
    # This matters in EDMC because load.py imports set_plugin_logger_name
    # from this package before plugin_start3 runs, which imports submodules
    # that create logger globals immediately.
    for module_name in (
        "src.edmcvkbconnector.config",
        "src.edmcvkbconnector.vkb_client",
        "src.edmcvkbconnector.event_handler",
        "src.edmcvkbconnector.rules_engine",
        "edmcvkbconnector.config",
        "edmcvkbconnector.vkb_client",
        "edmcvkbconnector.event_handler",
        "edmcvkbconnector.rules_engine",
    ):
        module = sys.modules.get(module_name)
        if module is None or not hasattr(module, "logger"):
            continue
        module.logger = plugin_logger(module.__name__)


def plugin_logger(module: str) -> logging.Logger:
    """Return a child logger under the plugin hierarchy.

    Usage in submodules::

        from edmcvkbconnector import plugin_logger
        logger = plugin_logger(__name__)

    Inside EDMC this yields e.g. ``EDMarketConnector.edmcvkbconnector.config``.
    During tests it yields ``edmcvkbconnector.config``.
    """
    # Always return the base plugin logger.
    # In EDMC this logger has EDMCContextFilter attached by
    # EDMCLogging.get_plugin_logger(), which adds fields like
    # osthreadid/qualname used by EDMC's log formatter.
    return logging.getLogger(_PLUGIN_LOGGER_NAME)

from .vkb_client import VKBClient
from .event_handler import EventHandler
from .config import Config
from .message_formatter import MessageFormatter, PlaceholderMessageFormatter

__all__ = [
    "VKBClient",
    "EventHandler",
    "Config",
    "MessageFormatter",
    "PlaceholderMessageFormatter",
]
