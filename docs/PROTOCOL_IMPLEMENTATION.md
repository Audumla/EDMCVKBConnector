# VKB-Link Protocol Implementation

This project implements the VKB-Link protocol used by the plugin as a fixed
`VKBShiftBitmap` packet.

## Status

- Protocol support in this plugin: **implemented and active**
- Message type: `VKBShiftBitmap`
- Transport: TCP

## Packet Format

For `event_type == "VKBShiftBitmap"`, the formatter emits 8 bytes:

```text
Byte 0: header      (default 0xA5, configurable)
Byte 1: command     (default 13, configurable)
Byte 2: reserved    (0)
Byte 3: data length (4)
Byte 4: shift       (bitmap)
Byte 5: subshift    (bitmap)
Byte 6: reserved    (0)
Byte 7: reserved    (0)
```

Configuration keys:
- `VKBConnector_vkb_header_byte`
- `VKBConnector_vkb_command_byte`

## Shift Encoding

- `Shift1` -> bit 0 in `shift`
- `Shift2` -> bit 1 in `shift`
- `Subshift1..7` -> bits 0..6 in `subshift`

The plugin sends only the masked values:
- `shift & 0x03`
- `subshift & 0x7F`

## Code Locations

- Formatter: `src/edmcruleengine/message_formatter.py`
- State + send path: `src/edmcruleengine/event_handler.py`
- Socket send path: `src/edmcruleengine/vkb_client.py`

## Validation Behavior

- Unsupported event types raise `ValueError` in the formatter.
- Only `VKBShiftBitmap` is serialized and sent to VKB-Link.
