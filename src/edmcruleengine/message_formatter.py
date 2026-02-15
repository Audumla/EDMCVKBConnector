"""
Message serialization for VKB-Link.

The VKB-Link protocol used by this plugin is fixed and implemented as
`VKBShiftBitmap` packets.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class MessageFormatter(ABC):
    """
    Formatter interface for VKB-Link message serialization.
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


class VKBLinkMessageFormatter(MessageFormatter):
    """
    Concrete formatter for the current VKB-Link protocol.

    Supported event:
    - `VKBShiftBitmap`
    """

    def __init__(self, *, header_byte: int = 0xA5, command_byte: int = 13) -> None:
        self.header_byte = header_byte & 0xFF
        self.command_byte = command_byte & 0xFF

    def format_event(self, event_type: str, event_data: Dict[str, Any]) -> bytes:
        """
        Format VKB shift/subshift bitmap packets.
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
