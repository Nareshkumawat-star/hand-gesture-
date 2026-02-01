"""
Sender Application
Detects hand gestures via webcam and sends selected file when pinch gesture is recognized
Camera closes after sending, receiver camera opens to accept
"""

import cv2
import os
import sys
import socket
import json
import time
from tkinter import Tk, filedialog
from gesture_detector import GestureDetector
from network_utils import DeviceDiscovery, FileTransfer
from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, TCP_PORT


class FileSender:
    """Main sender application with gesture detection and file transfer"""
    
    def __init__(self):
        self.gesture_detector = GestureDetector()
        self.selected_file = None
        self.receiver_ip = None
        self.receiver_port = None
        self.file_sent = False
        
    def select_file(self):
        """Open file dialog to select file for transfer"""
        print("\n" + "="*60)
        print("FILE SELECTION")
        print("="*60)
        
        # Hide the root Tkinter window
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select file to transfer",
            filetypes=[("All files", "*.*")]
        )
        
        root.destroy()
        
        if file_path:
            self.selected_file = file_path
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            print(f"✓ Selected: {os.path.basename(file_path)}")
            print(f"  Size: {file_size:.2f} MB")
            print(f"  Path: {file_path}")
            return True
        else:
            print("✗ No file selected")
            return False
    
    def get_receiver_ip(self):
        """Get receiver IP address - try discovery first, then ask user"""
        print("\n" + "="*60)
        print("RECEIVER CONNECTION")
        print("="*60)
        
        # Try auto-discovery first
        print("Searching for receiver on network...")
        self.receiver_ip, self.receiver_port = DeviceDiscovery.discover_receiver(timeout=5)
        
        if self.receiver_ip:
            # Check if same machine
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                if self.receiver_ip == local_ip:
                    print(f"  (Same machine detected)")
                    self.receiver_ip = "127.0.0.1"
            except:
                pass
            print(f"✓ Receiver found at {self.receiver_ip}:{self.receiver_port}")
            return True
        
        # Manual entry
        print("\nNo receiver found automatically.")
        print("Enter receiver IP address (or 'localhost' for same machine):")
        user_ip = input("> ").strip()
        
        if user_ip.lower() == 'localhost':
            user_ip = '127.0.0.1'
        
        if user_ip:
            self.receiver_ip = user_ip
            self.receiver_port = TCP_PORT
            print(f"✓ Will connect to {self.receiver_ip}:{self.receiver_port}")
            return True
        
        print("✗ No IP address provided")
        return False
    
    def notify_receiver_to_open_camera(self):
        """Send signal to receiver to open camera for gesture acceptance"""
        try:
            print(f"Connecting to receiver at {self.receiver_ip}:{self.receiver_port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 10 seconds to connect
            sock.connect((self.receiver_ip, self.receiver_port))
            print("✓ Connected to receiver")
            
            # Send camera open signal with file info
            signal = json.dumps({
                "type": "OPEN_CAMERA",
                "file_name": os.path.basename(self.selected_file),
                "file_size": os.path.getsize(self.selected_file),
                "sender_ip": socket.gethostbyname(socket.gethostname())
            }).encode()
            
            sock.sendall(len(signal).to_bytes(4, 'big'))
            sock.sendall(signal)
            print("Signal sent, waiting for receiver to accept with gesture...")
            print("(Receiver needs to make OPEN PINCH gesture)")
            print("(No timeout - waiting indefinitely...)")
            
            # Wait for receiver response - NO TIMEOUT (wait indefinitely)
            sock.settimeout(None)
            response_len_data = sock.recv(4)
            if not response_len_data:
                print("✗ No response from receiver")
                sock.close()
                return False
            response_len = int.from_bytes(response_len_data, 'big')
            response = json.loads(sock.recv(response_len).decode())
            
            sock.close()
            
            if response.get("type") == "ACCEPTED":
                print("✓ Receiver accepted!")
                return True
            else:
                print("✗ Receiver declined")
                return False
                
        except Exception as e:
            print(f"✗ Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_file_data(self):
        """Send the actual file data to receiver"""
        return FileTransfer.send_file(
            self.selected_file,
            self.receiver_ip,
            self.receiver_port
        )
    
    def start_gesture_detection(self):
        """Start camera and gesture detection loop"""
        print("\n" + "="*60)
        print("GESTURE DETECTION - SENDER")
        print("="*60)
        print("Starting camera...")
        
        # Open camera
        import platform
        if platform.system() == 'Windows':
            cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(CAMERA_INDEX)
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not cap.isOpened():
            print("✗ Error: Could not open camera")
            return False
        
        # Warmup camera
        print("Warming up camera...")
        for _ in range(10):
            cap.read()
            time.sleep(0.05)
        
        print("✓ Camera started")
        print("\nMake PINCH gesture (thumb + index finger) to send file")
        print("Press 'q' to cancel")
        
        window_name = "Sender - Make Pinch Gesture to Send"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        gesture_completed = False
        
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
                
                # Process for pinch gesture
                processed_frame, gesture_detected = self.gesture_detector.process_frame(frame)
                
                # Show file info
                if self.selected_file:
                    file_name = os.path.basename(self.selected_file)
                    cv2.putText(
                        processed_frame,
                        f"File: {file_name}",
                        (10, processed_frame.shape[0] - 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )
                    cv2.putText(
                        processed_frame,
                        f"To: {self.receiver_ip}",
                        (10, processed_frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )
                
                cv2.imshow(window_name, processed_frame)
                
                # Check if gesture completed
                if gesture_detected:
                    print("\n" + "="*60)
                    print("PINCH GESTURE COMPLETED!")
                    print("="*60)
                    gesture_completed = True
                    
                    # Show success message
                    cv2.putText(
                        processed_frame,
                        "PINCH COMPLETE - SENDING...",
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
                    print("\nCancelled by user")
                    break
                    
        except KeyboardInterrupt:
            print("\n\nInterrupted")
        finally:
            # CLOSE CAMERA after gesture
            print("Closing sender camera...")
            cap.release()
            cv2.destroyAllWindows()
            self.gesture_detector.cleanup()
            print("✓ Sender camera closed")
        
        return gesture_completed
    
    def run(self):
        """Main application flow"""
        print("\n" + "="*60)
        print("HAND GESTURE FILE SENDER")
        print("="*60)
        
        while True:  # Loop for multiple transfers
            # Step 1: Select file
            if not self.select_file():
                print("\nExiting - No file selected")
                break
            
            # Step 2: Get receiver IP (only first time or if not set)
            if not self.receiver_ip:
                if not self.get_receiver_ip():
                    print("\nExiting - No receiver IP")
                    break
            else:
                print(f"\n✓ Using receiver: {self.receiver_ip}:{self.receiver_port}")
            
            # Reset gesture detector for new transfer
            self.gesture_detector = GestureDetector()
            
            # Step 3: Start camera and wait for pinch gesture
            if not self.start_gesture_detection():
                print("\nGesture not completed")
                continue
            
            # Step 4: Notify receiver to open camera
            print("\n" + "="*60)
            print("WAITING FOR RECEIVER")
            print("="*60)
            print("Signaling receiver to open camera...")
            
            if self.notify_receiver_to_open_camera():
                # Step 5: Send file
                print("\n" + "="*60)
                print("SENDING FILE")
                print("="*60)
                
                if self.send_file_data():
                    print("\n✓ FILE SENT SUCCESSFULLY!")
                else:
                    print("\n✗ File transfer failed")
            else:
                print("\n✗ Receiver did not accept")
            
            # Ask user for next action
            print("\n" + "="*60)
            print("TRANSFER COMPLETE")
            print("="*60)
            print("\nWhat would you like to do?")
            print("  [n] Send another file")
            print("  [q] Quit")
            
            while True:
                choice = input("\nEnter choice (n/q): ").strip().lower()
                if choice == 'n':
                    self.file_sent = False
                    break
                elif choice == 'q':
                    print("\nExiting...")
                    print("\n" + "="*60)
                    print("APPLICATION CLOSED")
                    print("="*60)
                    return
                else:
                    print("Invalid choice. Enter 'n' for new file or 'q' to quit.")
        
        print("\n" + "="*60)
        print("APPLICATION CLOSED")
        print("="*60)


def main():
    """Entry point"""
    try:
        sender = FileSender()
        sender.run()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Keep window open
    print("\n")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
