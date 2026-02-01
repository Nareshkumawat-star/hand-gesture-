"""
Receiver Application
Broadcasts presence on network and receives files automatically
"""

import sys
import socket
from network_utils import DeviceDiscovery, FileTransfer
from config import RECEIVED_FILES_DIR


class FileReceiver:
    """Main receiver application with device broadcasting and file reception"""
    
    def __init__(self):
        self.discovery = DeviceDiscovery()
        self.device_name = "File Receiver"
        
    def get_local_ip(self):
        """Get local IP address"""
        try:
            # Connect to external address to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "Unable to determine"
    
    def run(self):
        """Main application flow"""
        print("\n" + "="*60)
        print("HAND GESTURE FILE RECEIVER")
        print("="*60)
        
        # Get local IP
        local_ip = self.get_local_ip()
        
        print(f"\nDevice Name: {self.device_name}")
        print(f"Local IP: {local_ip}")
        print(f"Received files will be saved to: {RECEIVED_FILES_DIR}/")
        
        print("\n" + "="*60)
        print("STARTING SERVICES")
        print("="*60)
        
        # Start broadcasting
        self.discovery.start_broadcast(self.device_name)
        
        print("\nReceiver is ready!")
        print("\nInstructions:")
        print("  1. This device is now discoverable on the network")
        print("  2. Run sender.py on another laptop (same Wi-Fi)")
        print("  3. Files will be received automatically")
        print("  4. Press Ctrl+C to stop")
        
        print("\n" + "="*60)
        print("WAITING FOR FILES...")
        print("="*60)
        
        try:
            # Start receiving files (blocking call)
            FileTransfer.receive_file(RECEIVED_FILES_DIR)
            
        except KeyboardInterrupt:
            print("\n\n" + "="*60)
            print("SHUTTING DOWN")
            print("="*60)
            self.discovery.stop_broadcast()
            print("✓ Broadcast stopped")
            print("✓ Receiver closed")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            self.discovery.stop_broadcast()
            sys.exit(1)
        
        print("\n" + "="*60)
        print("APPLICATION CLOSED")
        print("="*60)


def main():
    """Entry point"""
    try:
        receiver = FileReceiver()
        receiver.run()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
