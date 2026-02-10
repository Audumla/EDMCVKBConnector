"""
Message serialization abstraction for VKB protocol.

This module defines the interface for serializing events into the format
expected by VKB-Link. The exact protocol format is TBD pending VKB-Link
development of the TCP/IP communication interface.

When VKB-Link's protocol is finalized, implement a MessageFormatter
subclass with the actual bitmap/compact format specification.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class MessageFormatter(ABC):
    """
    Abstract base class for VKB message formatting.
    
    Defines the interface for converting EDMC events into the byte format
    expected by VKB-Link. The actual protocol will be defined once
    VKB-Link's TCP/IP communication is complete.
    """

    @abstractmethod
    def format_event(self, event_type: str, event_data: Dict[str, Any]) -> bytes:
        """
        Format an EDMC event into VKB protocol bytes.
        
        Args:
            event_type: Type of Elite Dangerous event (e.g., "FSDJump", "Location")
            event_data: Event data dictionary from EDMC
            
        Returns:
            Formatted message as bytes ready to send to VKB-Link
        """
        pass


class PlaceholderMessageFormatter(MessageFormatter):
    """
    Placeholder formatter for development.
    
    TODO: This will be replaced with the actual VKB protocol formatter
    once VKB-Link's TCP/IP interface specification is available.
    
    The protocol is expected to be:
    - Compact binary format with bitmap for message content
    - Small message size for efficient communication
    - Status indicators for hardware state
    """

    def format_event(self, event_type: str, event_data: Dict[str, Any]) -> bytes:
        """
        Placeholder: returns event type as UTF-8 bytes.
        
        This is a temporary implementation until the actual VKB protocol
        specification is documented. The final implementation will convert
        events into the compact bitmap format specified by VKB.
        """
        # Temporary placeholder: just send the event type
        # The final format will be determined by VKB-Link's protocol
        return f"{event_type}\n".encode("utf-8")
