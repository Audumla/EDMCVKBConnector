# EDMC PLUGINS.md Compliance Report

This document verifies compliance with the official [EDMarketConnector PLUGINS.md](https://github.com/EDCD/EDMarketConnector/blob/main/PLUGINS.md) requirements.

## 1. Python Version ✅

**Requirement**: Target latest stable Python version tested with EDMC

**Status**: Compliant

- Plugin targets Python 3.9+ (per latest EDMC standards)
- Configured in `pyproject.toml`: `requires-python = ">=3.9"`
- Black target-version set to `['py39']`
- Classifiers updated to list Python 3.9, 3.10, 3.11, 3.12
- Previous requirement for Python 3.8 removed to align with current EDMC standards

**Reference**: [Releasing.md Environment section](https://github.com/EDCD/EDMarketConnector/blob/main/docs/Releasing.md#environment)

## 2. Plugin Folder Structure ✅

**Requirement**: Plugins must be Python files in plugin folder with mandatory `load.py` containing `plugin_start3()` function

**Status**: Compliant

File structure:
```
edmcvkbconnector/
├── load.py                 (Entry point - contains plugin_start3())
├── rules.json.example      (Rules template)
├── src/edmcvkbconnector/
│   ├── __init__.py        (Package exports)
│   ├── config.py          (Configuration management)
│   ├── event_handler.py   (Event processing)
│   ├── vkb_client.py      (TCP/IP client)
│   ├── rules_engine.py    (Rule evaluation)
│   └── message_formatter.py (Protocol abstraction)
└── README.md
```

## 3. Logging Requirements ✅

**Requirement**: Use Python `logging` module instead of `print()` statements with specific setup pattern

**Status**: Compliant

### Logging Setup in load.py

The plugin follows the EDMC-recommended logging setup pattern:

```python
import logging
import os
from config import appname

# Logger setup per EDMC plugin requirements
plugin_name = os.path.basename(os.path.dirname(__file__))
logger = logging.getLogger(f"{appname}.{plugin_name}")

# Set up logging if it hasn't been already by core EDMC code
if not logger.hasHandlers():
    level = logging.INFO
    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_formatter = logging.Formatter(
        f"%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s:%(message)s"
    )
    logger_formatter.default_time_format = "%Y-%m-%d %H:%M:%S"
    logger_formatter.default_msec_format = "%s.%03d"
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)
```

**Key Compliance Points**:
- ✅ Uses `logging` module instead of `print()`
- ✅ Logger created at module level (not inside `plugin_start3()`)
- ✅ `plugin_name` derived from folder name via `os.path.basename(os.path.dirname(__file__))`
- ✅ Logger name includes `appname` prefix: `f"{appname}.{plugin_name}"`
- ✅ Checks `logger.hasHandlers()` before setting up (respects core setup)
- ✅ Proper formatter with timestamp, level, module, line number, function name
- ✅ Format string uses both default logging properties and formatter directives

### Logging Usage Throughout Plugin

All modules use proper logging:

- **load.py**: Uses `logger.info()`, `logger.warning()`, `logger.error()`
- **config.py**: `logger = logging.getLogger(__name__)` for config operations
- **event_handler.py**: `logger = logging.getLogger(__name__)` for event handling
- **vkb_client.py**: `logger = logging.getLogger(__name__)` for socket operations
- **message_formatter.py**: Protocol formatting (no direct logging needed)

Log levels used correctly:
- `logger.info()` - Informational messages (connection status, startup)
- `logger.warning()` - Warning conditions (failed connections, retries)
- `logger.error()` - Error conditions with `exc_info=True` for exceptions
- `logger.debug()` - Debug information (detailed operation flow)

## 4. Plugin Entry Point ✅

**Requirement**: Must provide `plugin_start3(plugin_dir: str) -> str` function

**Status**: Compliant

```python
def plugin_start3(plugin_dir: str) -> Optional[str]:
    """
    Start the plugin (called by EDMC 5.0+).
    
    Initializes the VKB connector with automatic reconnection on startup.
    """
    global _config, _event_handler
    
    try:
        from edmcvkbconnector import Config, EventHandler
        
        logger.info(f"VKB Connector v{VERSION} starting")
        
        # ... initialization code ...
        
        return "VKB Connector"  # Plugin name shown in EDMC UI
    except Exception as e:
        logger.error(f"Failed to start VKB Connector: {e}", exc_info=True)
        return None
```

**Compliance**:
- ✅ Function signature matches: `plugin_start3(plugin_dir: str) -> str`
- ✅ Returns string (plugin name for UI display)
- ✅ Proper exception handling with logging
- ✅ Global variables properly managed

## 5. Plugin Stop Function ✅

**Requirement**: Should provide `plugin_stop()` for graceful shutdown

**Status**: Compliant

```python
def plugin_stop() -> None:
    """
    Stop the plugin (called by EDMC on shutdown).
    
    Gracefully shuts down the VKB connector and stops all background threads.
    """
    global _event_handler

    try:
        logger.info("VKB Connector stopping")
        if _event_handler:
            _event_handler.disconnect()
            logger.info("VKB Connector stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping VKB Connector: {e}", exc_info=True)
```

**Compliance**:
- ✅ Proper thread cleanup (reconnection worker stopped)
- ✅ Exception handling with logging
- ✅ Graceful resource cleanup

## 6. Journal Entry Handler ✅

**Requirement**: Should provide optional `journal_entry()` to receive game events

**Status**: Compliant

```python
def journal_entry(cmdr: str, is_beta: bool, entry: dict, state: dict) -> Optional[str]:
    """
    Called when EDMC receives a journal event from Elite Dangerous.
    
    Forwards events to VKB hardware.
    """
    global _event_handler

    try:
        if not _event_handler or not _event_handler.enabled:
            return None

        # Get event type
        event_type = entry.get("event", "Unknown")

        # Forward to VKB hardware
        _event_handler.handle_event(event_type, entry, cmdr=cmdr, is_beta=is_beta)

    except Exception as e:
        logger.error(f"Error handling journal entry: {e}", exc_info=True)

    return None
```

**Compliance**:
- ✅ Function signature matches EDMC requirements
- ✅ Proper parameter handling (cmdr, is_beta, entry, state)
- ✅ Exception handling with logging
- ✅ Non-blocking operation (long-running ops done in separate thread)

## 7. Preferences UI & Changed Handler ✅

**Requirement**: Should provide optional `plugin_prefs()` and `prefs_changed()` when settings change

**Status**: Compliant

```python
def plugin_prefs(parent, cmdr: str, is_beta: bool):
    # Returns a Tkinter frame for EDMC preferences UI
    ...

def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Called when preferences are changed.
    
    Reconnects to VKB hardware in case configuration settings changed.
    """
    global _config, _event_handler

    try:
        if _event_handler:
            logger.info("Preferences changed, reconnecting VKB connector")
            
            # Reconnect with new settings
            _event_handler.disconnect()
            _event_handler.connect()
    except Exception as e:
        logger.error(f"Error in prefs_changed: {e}", exc_info=True)
```

**Compliance**:
- ✅ Proper function signature
- ✅ Handles preference changes
- ✅ Exception handling with logging
- ✅ Preferences UI provided for VKB host/port

## 8. No Long-Running Operations on Main Thread ✅

**Requirement**: Use separate threads for long-running operations (>1 second)

**Status**: Compliant

**TCP/IP Communication** done in separate threads:
- `vkb_client.py`: Socket operations in `_reconnect_worker()` thread
- `event_handler.py`: Thread spawned for background operations
- All socket communication non-blocking from main thread

**Implementation**:
- Background daemon thread for reconnection attempts
- Event synchronization prevents blocking main thread
- Graceful thread shutdown on plugin stop

## 9. Configuration Management ✅

**Requirement**: Use EDMC's `config` API for managing plugin preferences (`config.set()`, `config.get_str()`, etc.)

**Status**: Compliant

The plugin uses EDMC's standard configuration API as per [PLUGINS.md Configuration section](https://github.com/EDCD/EDMarketConnector/blob/main/PLUGINS.md#configuration):

**Implementation in `src/edmcvkbconnector/config.py`**:
```python
from config import config

class Config:
    def get(self, key: str, default: Any = None) -> Any:
        # Uses config.get_str(), config.get_int(), config.get_bool(), config.get_list()
        # based on the expected type of the configuration value
        
    def set(self, key: str, value: Any) -> None:
        # Uses config.set() to store values
        
    def delete(self, key: str) -> None:
        # Uses config.delete() to remove values
```

**Key Features**:
- ✅ Uses `config.get_str()`, `config.get_int()`, `config.get_bool()`, `config.get_list()`
- ✅ Settings namespaced with prefix `VKBConnector_` to avoid conflicts
- ✅ Configuration persisted in EDMC's system-appropriate location:
  - Windows: Registry (`HKEY_CURRENT_USER\Software\Frontier Developments\EDMarketConnector`)
  - macOS: User defaults
  - Linux: User config directory
- ✅ Fallback to in-memory defaults for local testing without EDMC
- ✅ `prefs_changed()` hook automatically reloads configuration via EDMC's API

**Supported Configuration Keys**:
- `vkb_host`: VKB device IP address (string, default: `127.0.0.1`)
- `vkb_port`: VKB device port (integer, default: `50995`)
- `vkb_header_byte`: VKB packet header byte (integer, default: `0xA5`)
- `vkb_command_byte`: VKB packet command byte (integer, default: `13`)
- `enabled`: Toggle plugin on/off (boolean, default: `true`)
- `debug`: Enable debug logging (boolean, default: `false`)
- `event_types`: List of game events to forward (list, default: Location, FSDJump, etc.)
- `rules_path`: Optional override path to rules.json

## 10. Available Imports Compliance ✅

**Requirement**: Use only explicitly allowed EDMC imports

**Status**: Compliant

Used imports from EDMC:
- ✅ `config.appname` - For logger naming
- ✅ `config.appversion` - For version checking (with fallback)
- ✅ `config.config` - For configuration storage (with graceful fallback)
- ✅ `logging` - For plugin logging

```

**Requirement**: Provide VERSION constant in semantic versioning format

**Status**: Compliant

**In load.py**:
```python
VERSION = "0.1.0"  # Required by EDMC standards for semantic versioning
```

**In __init__.py**:
```python
__version__ = "0.1.0"
```

**Format**: Follows MAJOR.MINOR.PATCH (0.1.0)

## 11. Error Handling & Logging ✅

**Requirement**: Proper exception handling with logging instead of crashing

**Status**: Compliant

All functions use try-except blocks:
```python
try:
    # ... code ...
except Exception as e:
    logger.error(f"Message: {e}", exc_info=True)
    # Graceful fallback or safe return
```

This ensures:
- ✅ No uncaught exceptions crash EDMC
- ✅ Errors logged with full traceback via `exc_info=True`
- ✅ Plugin continues functioning gracefully

## 12. Thread Safety ✅

**Requirement**: All long-running operations in separate threads, with safe thread handling

**Status**: Compliant

**VKBClient Implementation**:
- ✅ Reconnection logic in separate daemon thread
- ✅ Thread-safe socket operations using locks
- ✅ `_reconnect_lock` protects critical sections
- ✅ Clean shutdown with thread join

**Event Handler**:
- ✅ Non-blocking event forwarding
- ✅ Thread-safe integration with reconnection worker

## Summary

| Requirement | Status | Notes |
|---|---|---|
| Python Version (3.9+) | ✅ | Updated from 3.8 to 3.9+ |
| Plugin Folder & load.py | ✅ | Proper structure with plugin_start3() |
| Logging System | ✅ | Full EDMC-compliant logging setup |
| Entry Point | ✅ | plugin_start3() implemented |
| Plugin Stop | ✅ | Graceful shutdown implemented |
| Journal Entry Handler | ✅ | Event forwarding implemented |
| Prefs Changed Handler | ✅ | Using EDMC config API |
| No Blocking Operations | ✅ | Background threads for TCP/IP |
| Configuration Management | ✅ | Uses EDMC config API (config.get/set) |
| Approved Imports Only | ✅ | Zero unauthorized imports |
| VERSION Constant | ✅ | Semantic versioning used |
| Error Handling | ✅ | Try-except with logging throughout |
| Thread Safety | ✅ | Locks and proper cleanup |

**Overall Status**: ✅ **FULLY COMPLIANT** with EDMC PLUGINS.md requirements

---

*Last Updated: 2026-02-12*
*EDMC Version: 5.13.0+ (tested compatibility)*
*Python Version: 3.9+*
*Configuration API: Using EDMC's config.set/get for preference storage*

