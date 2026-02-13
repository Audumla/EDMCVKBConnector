"""Mock VKB hardware server for testing without real hardware."""

import socket
import threading
import time
import sys


class MockVKBServer:
    """Mock VKB server with data capture for test validation.
    
    Tracks all received messages for test inspection:
    - bytes_received: Total bytes count
    - messages: List of all messages received (preserves order, multiple clients)
    - clients: Dict mapping client address to list of messages from that client
    """
    
    def __init__(self, host="127.0.0.1", port=50995, verbose=True):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self.client_count = 0
        self.bytes_received = 0
        self.verbose = verbose
        self._lock = threading.Lock()
        
        # Message tracking for test validation
        self.messages = []  # All messages in order: [{"data": bytes, "addr": str, "timestamp": float}, ...]
        self.clients = {}   # Per-client messages: {addr_str: [{"data": bytes, "timestamp": float}, ...]}
    
    def _log(self, msg):
        """Log message if verbose mode enabled."""
        if self.verbose:
            try:
                print(msg)
            except UnicodeEncodeError:
                # Windows console encoding issue - remove unicode chars
                print(msg.encode('ascii', 'ignore').decode('ascii'))
    
    def start(self, duration=None):
        """Start the server."""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server.bind((self.host, self.port))
        except OSError as e:
            self._log(f"[FATAL] Failed to bind to {self.host}:{self.port}: {e}")
            self.running = False
            return
        
        self.server.listen(5)
        self.running = True
        
        self._log(f"[TARGET] Mock VKB Server listening on {self.host}:{self.port}")
        if duration:
            self._log(f"⏱️  Will run for {duration} seconds...")
        
        start_time = time.time()
        
        try:
            while self.running:
                if duration and (time.time() - start_time) > duration:
                    self._log(f"⏱️  Duration expired ({duration}s)")
                    break
                
                try:
                    self.server.settimeout(0.5)
                    client, addr = self.server.accept()
                    with self._lock:
                        self.client_count += 1
                    self._log(f"[CONNECT] Client #{self.client_count} connected: {addr}")
                    self._handle_client(client, addr)
                except socket.timeout:
                    continue
                except OSError:
                    # Server socket closed
                    break
        except KeyboardInterrupt:
            self._log("\n⏹️  Server stopped by user")
        except Exception as e:
            self._log(f"[FATAL] Server error: {e}")
        finally:
            self._close_socket()
    
    def _handle_client(self, client, addr):
        """Handle a connected client."""
        addr_str = f"{addr[0]}:{addr[1]}"
        try:
            while self.running:
                data = client.recv(1024)
                if not data:
                    break
                
                with self._lock:
                    self.bytes_received += len(data)
                    
                    # Store message for test inspection
                    timestamp = time.time()
                    message_info = {"data": data, "addr": addr_str, "timestamp": timestamp}
                    self.messages.append(message_info)
                    
                    # Also store per-client
                    if addr_str not in self.clients:
                        self.clients[addr_str] = []
                    self.clients[addr_str].append({"data": data, "timestamp": timestamp})
                
                hex_data = data.hex()
                
                # Parse header+command
                if len(data) >= 2:
                    header = data[0]
                    command = data[1]
                    payload = data[2:] if len(data) > 2 else b''
                    self._log(f"  [OK] Received {len(data)} bytes: "
                          f"Header=0x{header:02x}, Cmd=0x{command:02x}, "
                          f"Payload={payload.hex() if payload else 'none'}")
                else:
                    self._log(f"  [OK] Received {len(data)} bytes: {hex_data}")
                
                # Echo back simple ACK
                client.send(b"\x00\x01")
        except Exception as e:
            self._log(f"  [WARN] Client error: {e}")
        finally:
            client.close()
            self._log(f"[DISCONNECT] Client disconnected: {addr}")
    
    def _close_socket(self):
        """Close server socket safely."""
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass
        self._log(f"[STOP] Mock VKB Server stopped")
        self._log(f"[STATS] {self.client_count} clients, {self.bytes_received} bytes received")
    
    # ========== Query Methods for Test Validation ==========
    
    def get_messages(self):
        """Get all received messages in order.
        
        Returns:
            list: [{"data": bytes, "addr": str, "timestamp": float}, ...]
        """
        with self._lock:
            return list(self.messages)
    
    def get_client_messages(self, addr):
        """Get all messages from a specific client.
        
        Args:
            addr: Client address string (e.g., "127.0.0.1:12345")
            
        Returns:
            list: [{"data": bytes, "timestamp": float}, ...] or [] if no messages
        """
        with self._lock:
            return list(self.clients.get(addr, []))
    
    def get_message_count(self):
        """Get total number of messages received.
        
        Returns:
            int: Number of message chunks received
        """
        with self._lock:
            return len(self.messages)
    
    def get_client_count_messages(self, addr):
        """Get number of messages from a specific client.
        
        Args:
            addr: Client address string
            
        Returns:
            int: Number of messages from this client
        """
        with self._lock:
            return len(self.clients.get(addr, []))
    
    def clear_messages(self):
        """Clear all stored messages (for test reset/isolation).
        
        Note: bytes_received counter is NOT cleared - it represents total activity.
        """
        with self._lock:
            self.messages.clear()
            self.clients.clear()
    
    def has_received_data(self):
        """Quick check if any data has been received.
        
        Returns:
            bool: True if bytes_received > 0
        """
        with self._lock:
            return self.bytes_received > 0
    
    def find_messages_with_payload(self, payload_hex):
        """Find all messages containing a specific payload hex string.
        
        Args:
            payload_hex: Hex string to search for (e.g., "a50d")
            
        Returns:
            list: Messages matching the payload
        """
        with self._lock:
            matches = []
            for msg in self.messages:
                if payload_hex.lower() in msg["data"].hex().lower():
                    matches.append(msg)
            return matches
    
    def get_payload_bytes(self, message_index=0):
        """Extract payload bytes from a specific message (skipping header+command).
        
        Args:
            message_index: Index of message (0 = first message)
            
        Returns:
            bytes: Message payload (data[2:])
        """
        with self._lock:
            if message_index < len(self.messages):
                data = self.messages[message_index]["data"]
                return data[2:] if len(data) > 2 else b''
            return b''

    def stop(self):
        """Stop the server."""
        self.running = False
        self._close_socket()


def run_in_thread(host="127.0.0.1", port=50995, duration=30):
    """Start mock server in background thread."""
    server = MockVKBServer(host, port)
    thread = threading.Thread(
        target=server.start,
        kwargs={"duration": duration},
        daemon=True,
    )
    thread.start()
    time.sleep(0.5)  # Give server time to start
    return server, thread


if __name__ == "__main__":
    duration = None
    
    # Allow passing duration as argument: python mock_vkb_server.py 30
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print(f"Usage: python mock_vkb_server.py [duration_seconds]")
            print(f"Example: python mock_vkb_server.py 60")
            sys.exit(1)
    
    server = MockVKBServer()
    try:
        server.start(duration=duration)
    except KeyboardInterrupt:
        print("\nShutdown...")
