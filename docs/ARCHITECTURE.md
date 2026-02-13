# Architecture

This document describes the current runtime architecture of EDMCVKBConnector.

## Runtime Flow

```text
EDMC notification
  -> load.py hooks
  -> EventHandler
  -> Rules Engine (optional, rules.json)
  -> VKBClient
  -> VKBLinkMessageFormatter
  -> TCP socket to VKB-Link
```

## Components

- `load.py`
  - EDMC entry points (`plugin_start3`, `journal_entry`, `dashboard_entry`, etc.)
  - Preferences UI wiring
  - Plugin lifecycle

- `Config` (`src/edmcruleengine/config.py`)
  - EDMC-backed settings via `VKBConnector_*`
  - Defaults and typed reads/writes

- `EventHandler` (`src/edmcruleengine/event_handler.py`)
  - Event filtering (`enabled`, `event_types`)
  - Rule loading/reloading
  - Shift/subshift bitmap state
  - Emits `VKBShiftBitmap` payloads

- `DashboardRuleEngine` (`src/edmcruleengine/rules_engine.py`)
  - Evaluates `when` conditions (`flags`, `flags2`, `gui_focus`, `field`)
  - Executes `then` / `else` action sets

- `VKBClient` (`src/edmcruleengine/vkb_client.py`)
  - Socket connect/send/disconnect
  - Reconnection worker (2s initial, 10s fallback)

- `VKBLinkMessageFormatter` (`src/edmcruleengine/message_formatter.py`)
  - Serializes fixed VKB-Link `VKBShiftBitmap` packet format

## Protocol Position

Protocol handling is **implemented** and **fixed** in this codebase:
- message type: `VKBShiftBitmap`
- 8-byte packet with configurable header/command bytes
- no free-form event payloads are sent

Details: `docs/PROTOCOL_IMPLEMENTATION.md`.

## Reliability Model

- Connection loss marks client disconnected and triggers background reconnect.
- Reconnect worker runs until shutdown.
- Last sent shift/subshift values are tracked to avoid redundant sends.
- On reconnect, current bitmap state is re-sent.

## Configuration Model

Core keys:
- `vkb_host`, `vkb_port`
- `vkb_header_byte`, `vkb_command_byte`
- `enabled`, `debug`, `event_types`
- `rules_path`

Test UI state is persisted:
- `test_shift_bitmap`
- `test_subshift_bitmap`
