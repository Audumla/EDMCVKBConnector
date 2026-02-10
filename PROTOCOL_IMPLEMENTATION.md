# Protocol Implementation Guide

This document explains how the EDMCVKBConnector is designed to work with VKB-Link's TCP/IP protocol and how to implement the actual message format once it's specified.

## Current Status

**Protocol Status**: Under Development by VKB  
**Expected Format**: Compact binary with bitmap for message content  
**Current Implementation**: PlaceholderMessageFormatter

The exact protocol specification for VKB-Link's TCP/IP communication is still being finalized. This plugin uses an abstracted message formatter design that allows the protocol to be easily swapped in without changing the core event handling or networking logic.

## Architecture

### MessageFormatter Abstraction

The `MessageFormatter` is an abstract base class that defines the interface for converting EDMC events into VKB protocol bytes:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict

class MessageFormatter(ABC):
    @abstractmethod
    def format_event(self, event_type: str, event_data: Dict[str, Any]) -> bytes:
        """Format an EDMC event into VKB protocol bytes."""
        pass
```

This abstraction ensures:
- **Separation of Concerns**: Event handling is independent of wire format
- **Easy Updates**: When VKB protocol is finalized, only the formatter changes
- **Testability**: Formatters can be tested in isolation
- **Extensibility**: Multiple formatters can coexist for different protocol versions

### How VKBClient Uses Formatters

```python
class VKBClient:
    def __init__(self, host, port, message_formatter=None):
        if message_formatter is None:
            message_formatter = PlaceholderMessageFormatter()
        self.message_formatter = message_formatter
    
    def send_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        # Format using the configured formatter
        message_bytes = self.message_formatter.format_event(event_type, event_data)
        # Send bytes over TCP/IP
        self.socket.sendall(message_bytes)
```

## Implementing a Custom Formatter

When VKB-Link's protocol specification is available, implement a custom formatter by subclassing `MessageFormatter`:

### Step 1: Create the Formatter Class

```python
# In src/edmcvkbconnector/vkb_protocol.py

from edmcvkbconnector import MessageFormatter
from typing import Any, Dict

class VKBProtocolFormatter(MessageFormatter):
    """
    Implements the actual VKB-Link protocol.
    
    Protocol Specification:
    [Details from VKB-Link when available]
    """
    
    def format_event(self, event_type: str, event_data: Dict[str, Any]) -> bytes:
        """
        Format an EDMC event into VKB protocol binary format.
        
        Args:
            event_type: EDMC event type (e.g., "FSDJump", "Location")
            event_data: Full event data dictionary from EDMC
            
        Returns:
            Packed bytes ready to send to VKB-Link
        """
        # Implement the actual protocol here
        # Example (pseudocode):
        # - Extract relevant fields from event_data
        # - Build bitmap for message content
        # - Pack into compact binary format
        # - Return bytes
        
        pass
```

### Step 2: Map Events to Protocol Fields

Create helper methods to extract relevant data from EDMC events:

```python
class VKBProtocolFormatter(MessageFormatter):
    
    def _extract_ship_state(self, event_data: Dict[str, Any]) -> int:
        """Extract ship state bitmap from event data."""
        # Determine ship state from event
        # Return bitmap/state value
        pass
    
    def _extract_location(self, event_data: Dict[str, Any]) -> tuple:
        """Extract location info from event data."""
        # Get coords, system name, etc.
        pass
    
    def format_event(self, event_type: str, event_data: Dict[str, Any]) -> bytes:
        """Pack event into VKB protocol format."""
        import struct
        
        # Build message based on event type
        if event_type == "FSDJump":
            # Pack FSD jump data
            state = self._extract_ship_state(event_data)
            # ... build message
        elif event_type == "Location":
            # Pack location data
            # ... build message
        
        # Return packed bytes
        return struct.pack(...)  # Actual format TBD
```

### Step 3: Use the Custom Formatter

Update `load.py` or configuration to use the new formatter:

**Option A: In load.py**
```python
from edmcvkbconnector import EventHandler, Config, VKBClient
from edmcvkbconnector.vkb_protocol import VKBProtocolFormatter

def plugin_start3(plugin_dir: str) -> Optional[str]:
    config = Config(...)
    
    # Create client with VKB protocol formatter
    vkb_client = VKBClient(
        host=config.get("vkb_host"),
        port=config.get("vkb_port"),
        message_formatter=VKBProtocolFormatter()
    )
    
    event_handler = EventHandler(config, vkb_client)
    ...
```

**Option B: Configuration-based (future enhancement)**
```json
{
  "vkb_host": "127.0.0.1",
  "vkb_port": 12345,
  "message_formatter": "VKBProtocolFormatter",
  ...
}
```

## Testing the Implementation

### Unit Tests for Formatter

```python
import unittest
from edmcvkbconnector.vkb_protocol import VKBProtocolFormatter

class TestVKBProtocolFormatter(unittest.TestCase):
    
    def setUp(self):
        self.formatter = VKBProtocolFormatter()
    
    def test_format_fsd_jump(self):
        """Test FSD jump event formatting."""
        event_data = {
            "event": "FSDJump",
            "StarSystem": "Sol",
            "SystemAddress": 10477373803,
            # ... other fields
        }
        result = self.formatter.format_event("FSDJump", event_data)
        
        # Validate result is bytes
        self.assertIsInstance(result, bytes)
        # Validate message structure
        # ... protocol-specific assertions
    
    def test_format_location(self):
        """Test location event formatting."""
        event_data = {
            "event": "Location",
            "Docked": True,
            "StationName": "Helgoland Terminal",
            # ... other fields
        }
        result = self.formatter.format_event("Location", event_data)
        self.assertIsInstance(result, bytes)
```

### Integration Tests

```python
def test_vkb_client_with_custom_formatter(self):
    """Test VKBClient works with custom formatter."""
    from edmcvkbconnector import VKBClient
    from edmcvkbconnector.vkb_protocol import VKBProtocolFormatter
    
    formatter = VKBProtocolFormatter()
    client = VKBClient(message_formatter=formatter)
    
    # Test event sending (mock socket)
    event_data = {"event": "FSDJump", "StarSystem": "Sol"}
    # ... test implementation
```

## Protocol Specification Checklist

When VKB-Link's protocol is finalized, ensure it includes:

- ✅ Compact binary format specification
- ✅ Bitmap layout for message content flags
- ✅ Status field definitions
- ✅ Supported event types
- ✅ Field encoding details
- ✅ Message size constraints
- ✅ Error/acknowledgment responses (if any)
- ✅ Message ordering requirements
- ✅ Frequency/rate limiting

## Discovery and Monitoring

The plugin comes with logging capabilities to help with protocol development:

```json
{
  "debug": true
}
```

Enable this to see detailed logs of:
- Event types received
- Connection state changes
- Message send failures
- Reconnection attempts

These logs can help developers understand which events are being forwarded and verify the protocol implementation is working correctly.

## Backward Compatibility

When implementing the actual VKB protocol:

1. **Keep PlaceholderMessageFormatter**: Useful for fallback/debugging
2. **Add Version Checking**: If VKB-Link protocol evolves, support multiple versions
3. **Document Changes**: Update this guide with protocol details
4. **Test Thoroughly**: Ensure all event types work correctly

Example with version support:

```python
class VKBProtocolFormatter(MessageFormatter):
    """Implements VKB-Link protocol v1.0"""
    
    PROTOCOL_VERSION = 1
    
    def format_event(self, event_type: str, event_data: Dict[str, Any]) -> bytes:
        # Include version in message header
        # Allows future protocol versions to coexist
        pass

class VKBProtocolFormatterV2(MessageFormatter):
    """Implements VKB-Link protocol v2.0"""
    
    PROTOCOL_VERSION = 2
    
    def format_event(self, event_type: str, event_data: Dict[str, Any]) -> bytes:
        # Version 2 format
        pass
```

## References

- [VKB-Link Communication Spec](https://github.com/VKB-Industries/vkb-link) (link TBD)
- [EDMC Plugin API](https://github.com/EDCD/EDMarketConnector/wiki/Plugin-API)
- [Elite Dangerous Journal Format](https://github.com/EDCD/EDMC/blob/master/docs/examples)

---

**Last Updated**: 2025-02-10  
**Protocol Status**: Under Development  
**Next Step**: Await VKB-Link protocol specification
