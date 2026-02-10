"""
EDMC VKB Connector - Forward Elite Dangerous events to VKB hardware.

This extension forwards game events from EDMC to VKB hardware via TCP/IP socket connection.
"""

__version__ = "0.1.0"
__author__ = "EDMC VKB Connector Contributors"
__license__ = "MIT"

from .vkb_client import VKBClient
from .event_handler import EventHandler
from .config import Config

__all__ = ["VKBClient", "EventHandler", "Config"]
