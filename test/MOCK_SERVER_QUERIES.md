# Mock VKB Server - Query Methods for Test Validation

The `MockVKBServer` has been extended with query methods that allow tests to inspect received data and validate behavior without relying solely on bytes counters.

## Available Query Methods

### Basic State Queries

#### `get_message_count()` 
Get total number of message chunks received (not bytes, but message count).

```python
count = server.get_message_count()
assert count > 0, "No messages received"
```

#### `has_received_data()`
Quick boolean check if any data has been received.

```python
if server.has_received_data():
    print("Server received data")
```

### Message Inspection

#### `get_messages()`
Get all received messages in order. 

Returns: `[{"data": bytes, "addr": str, "timestamp": float}, ...]`

```python
messages = server.get_messages()
for msg in messages:
    print(f"From {msg['addr']}: {msg['data'].hex()}")
    print(f"Received at: {msg['timestamp']}")
```

#### `get_message_count()`, `get_client_count_messages(addr)`
Get total or per-client message counts.

```python
total = server.get_message_count()
from_client1 = server.get_client_count_messages("127.0.0.1:12345")
```

#### `get_client_messages(addr)`
Get all messages from a specific client.

Returns: `[{"data": bytes, "timestamp": float}, ...]`

```python
client_addr = "127.0.0.1:12345"
messages = server.get_client_messages(client_addr)
```

#### `get_payload_bytes(message_index=0)`
Extract payload bytes from a message (skips header+command bytes).

```python
payload = server.get_payload_bytes(0)  # First message's payload
assert len(payload) > 0
```

### Message Search

#### `find_messages_with_payload(payload_hex)`
Find all messages containing a specific hex payload.

```python
# Find all messages with VKBShiftBitmap command (0x0d)
matches = server.find_messages_with_payload("a50d")
assert len(matches) > 0, "No VKBShiftBitmap messages found"
```

### Message Management

#### `clear_messages()`
Clear stored message history (for test isolation).

Note: `bytes_received` counter is NOT cleared - it tracks total activity.

```python
server.clear_messages()
# Now get_message_count() returns 0, but bytes_received unchanged
```

---

## Usage Examples

### Example 1: Validate Data Reception

```python
def test_sends_data_correctly():
    with running_mock_server(port=50995) as server:
        client = VKBClient(port=50995)
        client.connect()
        
        # Send event
        client.send_event("VKBShiftBitmap", {"shift": 1})
        time.sleep(0.2)
        
        # Validate with query methods
        msg_count = server.get_message_count()
        assert msg_count > 0, "Message not received"
        
        messages = server.get_messages()
        first_msg = messages[0]
        print(f"Received: {first_msg['data'].hex()}")
        print(f"From: {first_msg['addr']}")
```

### Example 2: Multi-Client Validation

```python
def test_multiple_clients():
    with running_mock_server(port=50995) as server:
        client1 = VKBClient(host="127.0.0.1", port=50995)
        client2 = VKBClient(host="127.0.0.1", port=50995)
        
        client1.connect()
        client2.connect()
        
        client1.send_event("VKBShiftBitmap", {"shift": 1})
        client2.send_event("VKBShiftBitmap", {"shift": 2})
        time.sleep(0.2)
        
        # Total messages
        assert server.get_message_count() == 2
        
        # Per-client messages
        client1_addr = list(server.clients.keys())[0]
        client2_addr = list(server.clients.keys())[1]
        
        assert server.get_client_count_messages(client1_addr) == 1
        assert server.get_client_count_messages(client2_addr) == 1
```

### Example 3: Test Isolation with clear_messages()

```python
def test_isolation():
    with running_mock_server(port=50995) as server:
        # First test scenario
        client = VKBClient(port=50995)
        client.connect()
        client.send_event("VKBShiftBitmap", {"shift": 1})
        time.sleep(0.2)
        
        assert server.get_message_count() == 1
        
        # Reset for clean state (bytes_received still preserved)
        bytes_before_clear = server.bytes_received
        server.clear_messages()
        
        assert server.get_message_count() == 0
        assert server.bytes_received == bytes_before_clear  # Unchanged
        
        # Second test scenario
        client.send_event("VKBShiftBitmap", {"shift": 2})
        time.sleep(0.2)
        
        assert server.get_message_count() == 1  # Only the new message
```

### Example 4: Payload Inspection

```python
def test_payload_contents():
    with running_mock_server(port=50995) as server:
        client = VKBClient(port=50995)
        client.connect()
        
        # Send with specific shift
        client.send_event("VKBShiftBitmap", {"shift": 3})
        time.sleep(0.2)
        
        # Get all messages
        messages = server.get_messages()
        assert len(messages) > 0
        
        msg_hex = messages[0]['data'].hex()
        print(f"Full message: {msg_hex}")
        
        # Get just payload (skip header 0xa5 + command 0x0d)
        payload = server.get_payload_bytes(0)
        print(f"Payload only: {payload.hex()}")
        
        # Search for this payload in all messages
        matches = server.find_messages_with_payload(payload.hex())
        assert len(matches) > 0
```

---

## Property Access

You can also access raw properties directly (thread-safe access recommended):

```python
# Direct property access
total_bytes = server.bytes_received          # Total bytes counter
client_count = server.client_count           # Number of client connections
all_messages = server.messages               # List of all messages
per_client = server.clients                  # Dict of messages by client
```

---

## Thread Safety

All query methods use thread locks (`_lock`) to ensure thread-safe access to message data. The server runs client handlers in separate threads while the main test runs in the test thread.

```python
# Safe to call from test thread while server handles connections
while server.get_message_count() < expected_count:
    time.sleep(0.1)
```

---

## Integration with Reconnection Testing

The query methods help validate reconnection scenarios:

```python
def test_reconnection_transmission():
    with running_mock_server(port=50998) as server1:
        client = VKBClient(port=50998)
        client.connect()
        client.start_reconnection()
        
        client.send_event("VKBShiftBitmap", {"shift": 1})
        time.sleep(0.2)
        
        # Verify server1 received it
        assert server1.get_message_count() > 0
        msg1 = server1.get_messages()[0]
        print(f"Server1 got: {msg1['data'].hex()}")
    
    # Server1 closed, reconnecting...
    time.sleep(1)
    
    with running_mock_server(port=50998) as server2:
        # Server2 started
        # Wait for reconnection...
        
        time.sleep(0.5)
        
        # Send to server2
        client.send_event("VKBShiftBitmap", {"shift": 2})
        time.sleep(0.2)
        
        # Query what server2 got
        if server2.get_message_count() > 0:
            msg2 = server2.get_messages()[0]
            print(f"Server2 got: {msg2['data'].hex()}")
        else:
            print("Server2 got nothing (expected on same port due to TIME_WAIT)")
```

---

## Benefits

✅ **Detailed Validation** - Inspect exact bytes received, not just counts  
✅ **Message Ordering** - Verify message sequence in multi-client scenarios  
✅ **Payload Analysis** - Search for specific patterns in received data  
✅ **Test Isolation** - Clear messages between test phases while keeping bytes counted  
✅ **Thread-Safe** - Safe access from test thread while connections happen  
✅ **Debugging** - Easy inspection of what the server actually received  

---

## Backward Compatibility

Old tests using `server.bytes_received` continue to work unchanged. The new query methods are additions, not replacements.

```python
# Old style - still works
assert server.bytes_received > 0

# New style - more detailed
assert server.get_message_count() > 0
messages = server.get_messages()
```
