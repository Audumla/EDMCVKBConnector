"""
EDMC VKB Connector - Forward Elite Dangerous events to VKB hardware.

This extension forwards game events from EDMC to VKB hardware via TCP/IP socket connection.
The message format is abstracted and can be customized via MessageFormatter subclasses.
"""

import logging

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


def plugin_logger(module: str) -> logging.Logger:
    """Return a child logger under the plugin hierarchy.

    Usage in submodules::

        from edmcvkbconnector import plugin_logger
        logger = plugin_logger(__name__)

    Inside EDMC this yields e.g. ``EDMarketConnector.edmcvkbconnector.config``.
    During tests it yields ``edmcvkbconnector.config``.
    """
    # Strip the package prefix from __name__ so we don't get
    # "edmcvkbconnector.edmcvkbconnector.config".
    suffix = module.replace("edmcvkbconnector.", "").replace("edmcvkbconnector", "")
    if suffix:
        return logging.getLogger(f"{_PLUGIN_LOGGER_NAME}.{suffix}")
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
