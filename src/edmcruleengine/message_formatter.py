"""
Message serialization abstraction for VKB protocol.

This module defines the interface for serializing events into the format
expected by VKB-Link. The VKBShiftBitmap packet is implemented; other
messages remain abstracted for future protocol expansion.

When VKB-Link's protocol expands, implement a MessageFormatter subclass
with the additional bitmap/compact format specifications.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class MessageFormatter(ABC):
    """
    Abstract base class for VKB message formatting.
    
    Defines the interface for converting EDMC events into the byte format
    expected by VKB-Link. Additional protocol messages will be added as
    VKB-Link's TCP/IP communication is finalized.
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
    Placeholder formatter with VKBShiftBitmap support.
    
    Additional VKB protocol messages can be added here or via a
    dedicated formatter subclass as the specification evolves.
    """

    def __init__(self, *, header_byte: int = 0xA5, command_byte: int = 13) -> None:
        self.header_byte = header_byte & 0xFF
        self.command_byte = command_byte & 0xFF

    def format_event(self, event_type: str, event_data: Dict[str, Any]) -> bytes:
        """
        Formats VKB shift/subshift bitmap packets or falls back to text.
        """
        if event_type == "VKBShiftBitmap":
            shift = int(event_data.get("shift", 0)) & 0xFF
            subshift = int(event_data.get("subshift", 0)) & 0xFF
            return bytes([
                self.header_byte,   # header
                self.command_byte,  # CMD
                0,     # --
                4,     # data length (bytes)
                shift,
                subshift,
                0,
                0
            ])

        # Only VKBShiftBitmap is a valid VKB-Link protocol message.
        # Refuse to format unknown event types to prevent sending
        # non-protocol-safe payloads to VKB hardware.
        raise ValueError(
            f"Unsupported VKB event type '{event_type}'. "
            f"Only 'VKBShiftBitmap' is a valid VKB-Link protocol message."
        )
