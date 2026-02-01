"""
Network Utilities Module
Handles device discovery via UDP broadcast and file transfer via TCP sockets
"""

import socket
import threading
import os
import json
import time
from config import UDP_PORT, TCP_PORT, BROADCAST_INTERVAL, BUFFER_SIZE
from config import DISCOVERY_TIMEOUT, RECEIVED_FILES_DIR


class DeviceDiscovery:
    """Handles UDP broadcast for device discovery"""
    
    def __init__(self):
        self.is_broadcasting = False
        self.broadcast_thread = None
        
    def start_broadcast(self, device_name="Receiver"):
        """
        Start broadcasting presence on the network
        
        Args:
            device_name: Name to identify this device
        """
        self.is_broadcasting = True
        self.broadcast_thread = threading.Thread(
            target=self._broadcast_loop,
            args=(device_name,),
            daemon=True
        )
        self.broadcast_thread.start()
        print(f"[BROADCAST] Started broadcasting as '{device_name}'")
    
    def _broadcast_loop(self, device_name):
        """
        Continuously broadcast presence on UDP
        
        Args:
            device_name: Name to broadcast
        """
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Get local IP address
        try:
            # Connect to external address to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "127.0.0.1"
        
        message = json.dumps({
            "type": "RECEIVER_BROADCAST",
            "device_name": device_name,
            "ip": local_ip,
            "port": TCP_PORT
        }).encode()
        
        while self.is_broadcasting:
            try:
                sock.sendto(message, ('<broadcast>', UDP_PORT))
                time.sleep(BROADCAST_INTERVAL)
            except Exception as e:
                print(f"[BROADCAST ERROR] {e}")
                break
        
        sock.close()
    
    def stop_broadcast(self):
        """Stop broadcasting"""
        self.is_broadcasting = False
        if self.broadcast_thread:
            self.broadcast_thread.join(timeout=3)
        print("[BROADCAST] Stopped broadcasting")
    
    @staticmethod
    def discover_receiver(timeout=DISCOVERY_TIMEOUT):
        """
        Discover receiver on the network
        
        Args:
            timeout: Seconds to wait for discovery
            
        Returns:
            tuple: (receiver_ip, receiver_port) or (None, None) if not found
        """
        print(f"[DISCOVERY] Searching for receiver (timeout: {timeout}s)...")
        
        # Create UDP socket for listening
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', UDP_PORT))
        sock.settimeout(timeout)
        
        try:
            while True:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode())
                
                if message.get("type") == "RECEIVER_BROADCAST":
                    receiver_ip = message.get("ip")
                    receiver_port = message.get("port")
                    device_name = message.get("device_name")
                    
                    print(f"[DISCOVERY] Found receiver: {device_name} at {receiver_ip}:{receiver_port}")
                    sock.close()
                    return receiver_ip, receiver_port
                    
        except socket.timeout:
            print("[DISCOVERY] Timeout - No receiver found")
        except Exception as e:
            print(f"[DISCOVERY ERROR] {e}")
        finally:
            sock.close()
        
        return None, None


class FileTransfer:
    """Handles TCP file transfer"""
    
    @staticmethod
    def send_file(file_path, receiver_ip, receiver_port):
        """
        Send a file to the receiver via TCP
        
        Args:
            file_path: Path to file to send
            receiver_ip: IP address of receiver
            receiver_port: TCP port of receiver
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(file_path):
            print(f"[SEND ERROR] File not found: {file_path}")
            return False
        
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        
        print(f"[SEND] Connecting to {receiver_ip}:{receiver_port}...")
        
        try:
            # Create TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((receiver_ip, receiver_port))
            
            # Send file metadata
            metadata = json.dumps({
                "file_name": file_name,
                "file_size": file_size
            }).encode()
            
            sock.sendall(len(metadata).to_bytes(4, 'big'))
            sock.sendall(metadata)
            
            # Send file data
            print(f"[SEND] Sending {file_name} ({file_size} bytes)...")
            
            with open(file_path, 'rb') as f:
                sent_bytes = 0
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    
                    sock.sendall(chunk)
                    sent_bytes += len(chunk)
                    
                    # Show progress
                    progress = (sent_bytes / file_size) * 100
                    print(f"\r[SEND] Progress: {progress:.1f}%", end='')
            
            print(f"\n[SEND] File sent successfully!")
            sock.close()
            return True
            
        except Exception as e:
            print(f"\n[SEND ERROR] {e}")
            return False
    
    @staticmethod
    def receive_file(save_dir=RECEIVED_FILES_DIR):
        """
        Start TCP server to receive files
        
        Args:
            save_dir: Directory to save received files
        """
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Create TCP server socket
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('', TCP_PORT))
        server_sock.listen(5)
        
        print(f"[RECEIVE] Listening for file transfers on port {TCP_PORT}...")
        
        while True:
            try:
                # Accept connection
                client_sock, client_addr = server_sock.accept()
                print(f"\n[RECEIVE] Connection from {client_addr[0]}")
                
                # Receive metadata length
                metadata_len = int.from_bytes(client_sock.recv(4), 'big')
                
                # Receive metadata
                metadata = json.loads(client_sock.recv(metadata_len).decode())
                file_name = metadata["file_name"]
                file_size = metadata["file_size"]
                
                print(f"[RECEIVE] Receiving {file_name} ({file_size} bytes)...")
                
                # Receive file data
                save_path = os.path.join(save_dir, file_name)
                
                # Handle duplicate filenames
                counter = 1
                while os.path.exists(save_path):
                    name, ext = os.path.splitext(file_name)
                    save_path = os.path.join(save_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                with open(save_path, 'wb') as f:
                    received_bytes = 0
                    while received_bytes < file_size:
                        chunk = client_sock.recv(min(BUFFER_SIZE, file_size - received_bytes))
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        received_bytes += len(chunk)
                        
                        # Show progress
                        progress = (received_bytes / file_size) * 100
                        print(f"\r[RECEIVE] Progress: {progress:.1f}%", end='')
                
                print(f"\n[RECEIVE] File saved to: {save_path}")
                print(f"[RECEIVE] Waiting for next file...")
                
                client_sock.close()
                
            except KeyboardInterrupt:
                print("\n[RECEIVE] Shutting down...")
                break
            except Exception as e:
                print(f"\n[RECEIVE ERROR] {e}")
                continue
        
        server_sock.close()
