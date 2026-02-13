# Architecture & Design

This document explains the design decisions and architecture patterns used in EDMCVKBConnector.

## Key Design Principles

### 1. Protocol Abstraction

The plugin uses the **Strategy Pattern** to abstract the message format used for VKB-Link communication.

**Problem**: VKB-Link's TCP/IP protocol is still under development. We need flexibility to swap implementations without changing event handling logic.

**Solution**: `MessageFormatter` abstract base class defines the interface, allowing multiple implementations:

```python
# Interface
class MessageFormatter(ABC):
    def format_event(self, event_type: str, event_data: Dict) -> bytes:
        pass

# Implementation A: Placeholder (current)
class PlaceholderMessageFormatter(MessageFormatter):
    pass

# Implementation B: Actual VKB protocol (future)
class VKBProtocolFormatter(MessageFormatter):
    pass
```

**Benefits**:
- Core logic (VKBClient, EventHandler, load.py) never references JSON or specific format
- Protocol changes require only new MessageFormatter subclass
- Multiple protocol versions can coexist
- Easy to test each formatter independently
- Plugin works before final protocol specification

### 2. Separation of Concerns

Each module has a single, well-defined responsibility:

```
Event Source (EDMC)
    ↓
load.py (Plugin Lifecycle)
    ↓
EventHandler (Event Filtering)
    ↓
VKBClient (Network Communication)
    ├─ Socket Management (connect/disconnect/send)
    ├─ Connection Resilience (reconnection logic)
    └─ Message Delegation (formatting)
        ↓
    MessageFormatter (Protocol Serialization)
        ↓
TCP/IP to VKB-Link
```

### 3. Fault Tolerance Through Resilience

The plugin implements a multi-layer fault tolerance strategy:

**Layer 1: Connection Management**
- Automatic reconnection on disconnection
- Exponential backoff (2s initial, 10s fallback)
- Background worker thread for non-blocking retries

**Layer 2: Error Handling**
- Specific exception types (not generic `Exception`)
- Graceful degradation (plugin continues running)
- Clear logging for debugging

**Layer 3: Thread Safety**
- Locks protect critical sections (socket access)
- Thread-safe primitives (Event for synchronization)
- Proper cleanup (daemon threads, join on shutdown)

### 4. Configuration-Driven Behavior

Runtime behavior is controlled via configuration, not code:

Core settings are stored via EDMC's config API with the `VKBConnector_` prefix:

- `vkb_host`, `vkb_port`: Network target
- `vkb_header_byte`, `vkb_command_byte`: Protocol header/command bytes
- `enabled`, `debug`, `event_types`: Feature toggles and event filtering
- `rules_path`: Optional override path for `rules.json`

Dynamic rules live in `rules.json` in the plugin directory.

**Benefits**:
- No code changes needed for different deployments
- Easy to disable plugin without uninstalling
- Debug mode for troubleshooting
- Granular event filtering

### 5. Type Safety

The plugin uses Python type hints throughout:

```python
def send_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
    ...

class VKBClient:
    socket: Optional[socket.socket] = None
    _reconnect_thread: Optional[threading.Thread] = None
```

**Benefits**:
- IDE autocomplete and refactoring support
- Static type checking with mypy
- Self-documenting code
- Easier to debug type-related issues

## Class Hierarchy

```
MessageFormatter (ABC)
├─ PlaceholderMessageFormatter
└─ VKBProtocolFormatter (future)

VKBClient
├─ connect(): bool
├─ disconnect(): None
├─ send_event(event_type, event_data): bool
├─ start_reconnection(): None
└─ _reconnect_worker(): None

EventHandler
├─ connect(): bool
├─ disconnect(): None
├─ handle_event(event_type, event_data): None
├─ enable(): None
├─ disable(): None
└─ set_debug(enabled): None

Config
├─ get(key, default): Any
├─ set(key, value): None
├─ delete(key): None
└─ __getitem__/__setitem__: Dictionary-like access

EDMC Integration (load.py)
├─ plugin_start3(plugin_dir): Optional[str]
├─ plugin_stop(): None
├─ plugin_prefs(parent, cmdr, is_beta): Frame
├─ prefs_changed(cmdr, is_beta): None
└─ journal_entry(cmdr, is_beta, entry, state): Optional[str]
```

## Data Flow

### Startup
```
EDMC loads load.py
    ↓
plugin_start3() called
    ↓
Config loads EDMC preferences
    ↓
EventHandler created with Config
    ├─ rules.json loaded (or override path)
    └─ shift/subshift state initialized
    ↓
VKBClient created with PlaceholderMessageFormatter (header/command bytes configurable)
    ↓
EventHandler.connect() called
    ├─ VKBClient.connect() attempts initial connection
    └─ VKBClient.start_reconnection() starts background worker
    
Result: "Plugin started (connection succeeded or pending reconnection)"
```

### Event Processing
```
Elite Dangerous generates journal event
    ↓
EDMC calls journal_entry(cmdr, is_beta, entry, state)
    ↓
EventHandler.handle_event(event_type, entry) called
    ├─ Check if enabled
    ├─ Filter by event_types (if configured)
    ├─ Rules Engine evaluates dashboard/status data
    │   ├─ then/else actions applied
    │   └─ Shift/subshift bitmap sent as VKBShiftBitmap
    └─ VKBClient.send_event(event_type, entry) called
        ├─ Check if connected
        ├─ MessageFormatter.format_event(event_type, entry) called
        │   Returns: bytes (VKBShiftBitmap uses 8-byte header/command format)
        └─ socket.sendall(bytes)
        
Result: Event forwarded to VKB-Link (or logged as error if not connected)
```

### Connection Loss & Reconnection
```
socket.sendall() raises OSError
    ↓
VKBClient.send_event() catches exception
    ↓
Sets reconnection event
    ├─ connected = False
    ├─ _reconnect_event.set()
    └─ Starts reconnection thread if not running
        
Background reconnection worker loop:
    while not _stop_event.is_set():
        ├─ Check if reconnection needed (_reconnect_event.is_set())
        ├─ Determine retry interval (2s or 10s based on duration)
        ├─ Call connect() if interval elapsed
        ├─ If successful: set connected=True, clear _reconnect_event
        ├─ If failed: update _last_connection_attempt timestamp
        └─ Sleep 0.5s (efficient backoff)

Result: Automatic reconnection with minimal resource usage
```

### Shutdown
```
EDMC exits
    ↓
plugin_stop() called
    ↓
EventHandler.disconnect() called
    ├─ VKBClient.disconnect() called
    │   ├─ _stop_event.set() (signals worker thread)
    │   └─ Waits for worker thread to finish (timeout 5s)
    └─ Closes socket gracefully

Result: Clean shutdown, no hanging threads
```

## Design Patterns Used

### 1. Strategy Pattern
**Where**: MessageFormatter and implementations  
**Why**: Easily swap different serialization strategies

### 2. Template Method Pattern  
**Where**: load.py plugin entry points  
**Why**: EDMC defines skeleton, we fill in methods

### 3. Factory Pattern
**Where**: VKBClient initialization with optional formatter  
**Why**: Default PlaceholderMessageFormatter if not provided

### 4. Observer Pattern
**Where**: EDMC journal_entry events  
**Why**: Respond to game events asynchronously

### 5. Command Pattern
**Where**: EventHandler commands (enable, disable, set_debug)  
**Why**: Encapsulate parameter changes as objects

### 6. Worker Thread Pattern
**Where**: Background reconnection thread  
**Why**: Non-blocking retry logic without callback hell

## Thread Safety Considerations

The plugin is thread-safe for concurrent access:

```python
# Protected by locks
class VKBClient:
    _reconnect_lock = threading.Lock()
    
    def send_event(self):
        with self._reconnect_lock:
            # Only one thread accesses socket at a time
            self.socket.sendall(...)
    
    def connect(self):
        with self._reconnect_lock:
            # Connect/reconnect is atomic
            self._close_socket()
            self.socket = socket.socket(...)
```

**Usage patterns**:
- Multiple EDMC event threads can call `send_event()` concurrently
- Background reconnection thread safely manages connection state
- No race conditions or deadlocks

## Performance Considerations

### Memory Efficiency
- No event buffering (messages sent immediately)
- Minimal state (only connection and formatter)
- Daemon threads automatically cleaned up

### Network Efficiency
- Single TCP connection reused for all events
- No connection overhead per event
- Minimal message overhead (depends on MessageFormatter)

### CPU Efficiency
- Reconnection uses exponential backoff (0.5s sleep)
- Event processing is O(1) per event
- No busy-waiting or polling

## Future Enhancements

1. **Message Buffering**: Queue events if disconnected, flush on reconnect
2. **Connection Pooling**: Support multiple VKB devices
3. **Protocol Discovery**: Auto-detect VKB-Link protocol version
4. **Health Checks**: Periodic ping to verify connection health
5. **Rate Limiting**: Throttle high-frequency events
6. **Event Batching**: Group events into single messages
7. **Acknowledgments**: Wait for VKB-Link response before considering sent

## Security Considerations

1. **Network Security**:
   - Local network only (configurable host)
   - No authentication (runs on local network)
   - Consider firewall rules

2. **Code Security**:
   - No privilege escalation
   - No external command execution
   - Only reads game data, writes to VKB-Link

3. **Data Security**:
   - No personal data stored
   - Event data immediately transmitted (no logging)
   - Debug mode available for investigation

---

## References

- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)
- [Template Method Pattern](https://refactoring.guru/design-patterns/template-method)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Thread Safety in Python](https://docs.python.org/3/library/threading.html)
- [EDMC Plugin Architecture](https://github.com/EDCD/EDMarketConnector/wiki)

---

**Last Updated**: 2026-02-12  
**Maintainers**: EDMC VKB Connector Contributors
