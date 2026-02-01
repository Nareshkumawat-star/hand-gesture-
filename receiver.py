"""
Receiver Application
Opens camera when sender signals, waits for open pinch gesture to accept file
"""

import sys
import socket
import json
import os
import cv2
import time
import platform
import threading
from gesture_detector import GestureDetector
from network_utils import DeviceDiscovery, get_local_ip
from config import RECEIVED_FILES_DIR, TCP_PORT, BUFFER_SIZE
from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT


class FileReceiver:
    """Main receiver application with gesture-based file acceptance"""
    
    def __init__(self):
        self.discovery = DeviceDiscovery()
        self.device_name = "File Receiver"
        self.gesture_detector = None
        self.server_sock = None  # Main server socket
        
    def get_local_ip(self):
        """Get local IP address"""
        return get_local_ip()
    
    def wait_for_open_pinch_gesture(self, file_info):
        """Open camera and wait for open pinch gesture to accept file"""
        print("\n" + "="*60)
        print("OPEN CAMERA FOR GESTURE")
        print("="*60)
        
        # Wait for sender camera to fully release (important for EXE/same machine)
        print("\nWaiting for sender camera to release...")
        for i in range(3, 0, -1):
            print(f"  Opening in {i}...")
            time.sleep(1)
        
        print("Initializing MediaPipe...")
        # Initialize gesture detector
        try:
            self.gesture_detector = GestureDetector()
            print("✓ MediaPipe initialized")
        except Exception as e:
            print(f"✗ MediaPipe init failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        print("Starting camera...")
        
        # Open camera with retry
        cap = None
        for attempt in range(10):  # Increase retries to 10
            try:
                if platform.system() == 'Windows':
                    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(CAMERA_INDEX)
                
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                if cap.isOpened():
                    # Try to read a frame to confirm it works
                    ret, _ = cap.read()
                    if ret:
                        print(f"✓ Camera opened on attempt {attempt + 1}")
                        break
                    else:
                        print(f"  Camera opened but failed to read frame...")
                        cap.release()
                else:
                    print(f"  Retry {attempt + 1}/10 - camera not ready...")
                
                time.sleep(1)
            except Exception as e:
                print(f"  Camera error attempt {attempt+1}: {e}")
                time.sleep(1)
        
        if not cap or not cap.isOpened():
            print("✗ Error: Could not open camera after retries")
            print("  Check if sender camera is truly closed")
            try:
                self.gesture_detector.cleanup()
            except:
                pass
            return False
        
        # Warmup
        print("Warming up camera...")
        for _ in range(5):
            cap.read()
            time.sleep(0.05)
        
        print("✓ Camera started")
        print(f"\nIncoming file: {file_info.get('file_name', 'Unknown')}")
        print(f"From: {file_info.get('sender_ip', 'Unknown')}")
        print("\nMake OPEN PINCH gesture (spread thumb & index) to ACCEPT")
        print("Press 'q' to DECLINE")
        
        window_name = "Receiver - Open Pinch to Accept"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        gesture_accepted = False
        
        try:
            consecutive_failures = 0
            max_failures = 30
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        print("✗ Camera read failed")
                        break
                    time.sleep(0.033)
                    continue
                
                consecutive_failures = 0
                frame = cv2.flip(frame, 1)
                
                # Process for open pinch gesture
                processed_frame, gesture_detected = self.gesture_detector.process_frame_open_pinch(
                    frame, 
                    pending_info=file_info
                )
                
                cv2.imshow(window_name, processed_frame)
                
                # Check if gesture completed
                if gesture_detected:
                    print("\n" + "="*60)
                    print("OPEN PINCH DETECTED - ACCEPTING FILE!")
                    print("="*60)
                    gesture_accepted = True
                    
                    # Show acceptance message
                    cv2.putText(
                        processed_frame,
                        "ACCEPTED! Receiving file...",
                        (10, 100),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2
                    )
                    cv2.imshow(window_name, processed_frame)
                    cv2.waitKey(1000)
                    break
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nFile declined by user")
                    break
                    
        except KeyboardInterrupt:
            print("\n\nInterrupted")
        finally:
            # Close camera
            print("Closing receiver camera...")
            cap.release()
            cv2.destroyAllWindows()
            self.gesture_detector.cleanup()
            self.gesture_detector = None
            print("✓ Receiver camera closed")
        
        return gesture_accepted
    
    def receive_file_from_socket(self, client_sock, file_info):
        """Receive file data from an existing socket connection"""
        print("\n" + "="*60)
        print("RECEIVING FILE")
        print("="*60)
        
        # Create save directory
        os.makedirs(RECEIVED_FILES_DIR, exist_ok=True)
        
        file_name = file_info.get("file_name", "unknown_file")
        file_size = file_info.get("file_size", 0)
        
        print(f"[RECEIVE] Receiving {file_name} ({file_size} bytes)...")
        
        # Save file
        save_path = os.path.join(RECEIVED_FILES_DIR, file_name)
        counter = 1
        while os.path.exists(save_path):
            name, ext = os.path.splitext(file_name)
            save_path = os.path.join(RECEIVED_FILES_DIR, f"{name}_{counter}{ext}")
            counter += 1
        
        try:
            with open(save_path, 'wb') as f:
                received_bytes = 0
                while received_bytes < file_size:
                    chunk = client_sock.recv(min(BUFFER_SIZE, file_size - received_bytes))
                    if not chunk:
                        break
                    f.write(chunk)
                    received_bytes += len(chunk)
                    progress = (received_bytes / file_size) * 100
                    print(f"\r[RECEIVE] Progress: {progress:.1f}%", end='')
            
            print(f"\n[RECEIVE] ✓ File saved to: {save_path}")
            return True
        except Exception as e:
            print(f"\n[RECEIVE ERROR] {e}")
            return False
    
    def handle_connection(self, client_sock, client_addr):
        """Handle incoming connection from sender"""
        try:
            # Receive signal length
            client_sock.settimeout(10)
            signal_len_data = client_sock.recv(4)
            if not signal_len_data:
                client_sock.close()
                return
            signal_len = int.from_bytes(signal_len_data, 'big')
            
            # Receive signal
            signal_data = client_sock.recv(signal_len)
            signal = json.loads(signal_data.decode())
            
            if signal.get("type") == "OPEN_CAMERA":
                # Sender wants us to accept file with gesture
                file_info = {
                    "file_name": signal.get("file_name", "Unknown"),
                    "file_size": signal.get("file_size", 0),
                    "sender_ip": client_addr[0]
                }
                
                print(f"\n[INCOMING] File transfer request from {client_addr[0]}")
                print(f"  File: {file_info['file_name']}")
                print(f"  Size: {file_info['file_size'] / (1024*1024):.2f} MB")
                
                # Open camera and wait for gesture
                accepted = self.wait_for_open_pinch_gesture(file_info)
                
                # Send response to sender
                if accepted:
                    response = json.dumps({"type": "ACCEPTED"}).encode()
                else:
                    response = json.dumps({"type": "DECLINED"}).encode()
                
                client_sock.sendall(len(response).to_bytes(4, 'big'))
                client_sock.sendall(response)
                client_sock.close()
                
                if accepted:
                    # Wait for sender to connect again with file data
                    print("\nWaiting for file data...")
                    try:
                        self.server_sock.settimeout(30)
                        file_sock, file_addr = self.server_sock.accept()
                        print(f"[RECEIVE] Connection from {file_addr[0]}")
                        
                        # Receive metadata
                        metadata_len = int.from_bytes(file_sock.recv(4), 'big')
                        metadata = json.loads(file_sock.recv(metadata_len).decode())
                        
                        file_info["file_name"] = metadata["file_name"]
                        file_info["file_size"] = metadata["file_size"]
                        
                        # Receive file
                        self.receive_file_from_socket(file_sock, file_info)
                        file_sock.close()
                        
                    except socket.timeout:
                        print("[RECEIVE] Timeout waiting for file data")
                    except Exception as e:
                        print(f"[RECEIVE ERROR] {e}")
                    finally:
                        self.server_sock.settimeout(None)
                        
            else:
                # Unknown signal type
                print(f"[WARNING] Unknown signal type: {signal.get('type')}")
                client_sock.close()
                
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
            try:
                client_sock.close()
            except:
                pass
    
    def run(self):
        """Main application flow"""
        print("\n" + "="*60)
        print("HAND GESTURE FILE RECEIVER")
        print("="*60)
        
        local_ip = self.get_local_ip()
        
        print(f"\nDevice Name: {self.device_name}")
        print(f"Local IP: {local_ip}")
        print(f"Port: {TCP_PORT}")
        print(f"Files saved to: {RECEIVED_FILES_DIR}/")
        
        print("\n" + "="*60)
        print("STARTING SERVICES")
        print("="*60)
        
        # Start broadcasting
        self.discovery.start_broadcast(self.device_name)
        
        # Create main server socket
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(('', TCP_PORT))
        self.server_sock.listen(5)
        
        print("\n✓ Receiver is ready!")
        print("\nWaiting for sender to connect...")
        print("When sender makes pinch gesture, your camera will open.")
        print("Make OPEN PINCH gesture to accept the file.")
        print("\nPress Ctrl+C to stop")
        
        try:
            while True:
                client_sock, client_addr = self.server_sock.accept()
                print(f"\n[CONNECTION] From {client_addr[0]}")
                
                # Handle connection directly (not in thread for clarity)
                self.handle_connection(client_sock, client_addr)
                
                print("\n" + "="*60)
                print("WAITING FOR NEXT FILE...")
                print("="*60)
                
        except KeyboardInterrupt:
            print("\n\n" + "="*60)
            print("SHUTTING DOWN")
            print("="*60)
            self.discovery.stop_broadcast()
            self.server_sock.close()
            print("✓ Receiver closed")
        
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
    
    # Keep window open
    print("\n")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
