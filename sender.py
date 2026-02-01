"""
Sender Application
Detects hand gestures via webcam and sends selected file when pinch gesture is recognized
"""

import cv2
import os
import sys
from tkinter import Tk, filedialog
from gesture_detector import GestureDetector
from network_utils import DeviceDiscovery, FileTransfer
from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT


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
    
    def discover_receiver(self):
        """Discover receiver on the network"""
        print("\n" + "="*60)
        print("DEVICE DISCOVERY")
        print("="*60)
        print("Searching for receiver on the network...")
        print("(Make sure receiver is running on another laptop)")
        
        self.receiver_ip, self.receiver_port = DeviceDiscovery.discover_receiver()
        
        if self.receiver_ip:
            print(f"✓ Receiver found at {self.receiver_ip}:{self.receiver_port}")
            return True
        else:
            print("✗ No receiver found")
            print("\nTroubleshooting:")
            print("  1. Ensure receiver.py is running on another laptop")
            print("  2. Both laptops must be on the same Wi-Fi network")
            print("  3. Check firewall settings")
            return False
    
    def start_gesture_detection(self):
        """Start camera and gesture detection loop"""
        print("\n" + "="*60)
        print("GESTURE DETECTION")
        print("="*60)
        print("Starting camera...")
        
        # Open camera
        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        
        if not cap.isOpened():
            print("✗ Error: Could not open camera")
            return
        
        print("✓ Camera started successfully")
        print("\nInstructions:")
        print("  1. Show your hand to the camera")
        print("  2. Make a PINCH gesture (thumb + index finger)")
        print("  3. Hold for 0.5 seconds to trigger file transfer")
        print("  4. Press 'q' to quit")
        print("\nWaiting for gesture...")
        
        window_name = "Hand Gesture File Sender"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        try:
            # Warmup: give camera time to initialize
            import time
            time.sleep(0.5)
            
            # Track consecutive failures for retry logic
            consecutive_failures = 0
            max_failures = 30  # Allow up to 30 failures (~1 second) before giving up
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        print("✗ Error: Failed to read frame after multiple attempts")
                        break
                    time.sleep(0.033)  # Wait ~1 frame at 30fps
                    continue
                
                # Reset failure counter on successful read
                consecutive_failures = 0
                
                # Flip frame horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Process frame for gesture detection
                processed_frame, gesture_detected = self.gesture_detector.process_frame(frame)
                
                # Add file info to frame
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
                
                if self.receiver_ip:
                    cv2.putText(
                        processed_frame,
                        f"Receiver: {self.receiver_ip}",
                        (10, processed_frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )
                
                # Display frame
                cv2.imshow(window_name, processed_frame)
                
                # Check if gesture was detected
                if gesture_detected and not self.file_sent:
                    print("\n" + "="*60)
                    print("GESTURE DETECTED - INITIATING FILE TRANSFER")
                    print("="*60)
                    
                    # Send file
                    success = FileTransfer.send_file(
                        self.selected_file,
                        self.receiver_ip,
                        self.receiver_port
                    )
                    
                    if success:
                        print("✓ File transfer completed successfully!")
                        self.file_sent = True
                        
                        # Add success message to frame
                        cv2.putText(
                            processed_frame,
                            "FILE SENT SUCCESSFULLY!",
                            (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0, 255, 0),
                            2
                        )
                        cv2.imshow(window_name, processed_frame)
                        cv2.waitKey(2000)  # Show success message for 2 seconds
                        
                        # Automatically select new file
                        print("\nAutomatically opening file selection...")
                        
                        # Small delay to ensure UI updates
                        cv2.waitKey(100)
                        
                        if self.select_file():
                            self.file_sent = False
                            self.gesture_detector.reset_gesture()
                            print("\nReady for gesture detection...")
                        else:
                            print("\nNo file selected. Press 'n' for new file, or 'q' to quit")
                    else:
                        print("✗ File transfer failed")
                        self.gesture_detector.reset_gesture()
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nQuitting...")
                    break
                elif key == ord('n') and self.file_sent:
                    # Select new file
                    if self.select_file():
                        self.file_sent = False
                        self.gesture_detector.reset_gesture()
                        print("\nReady for gesture detection...")
                    
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        finally:
            # Cleanup
            cap.release()
            cv2.destroyAllWindows()
            self.gesture_detector.cleanup()
    
    def run(self):
        """Main application flow"""
        print("\n" + "="*60)
        print("HAND GESTURE FILE SENDER")
        print("="*60)
        
        # Step 1: Select file
        if not self.select_file():
            print("\nExiting - No file selected")
            return
        
        # Step 2: Discover receiver
        if not self.discover_receiver():
            print("\nExiting - No receiver found")
            return
        
        # Step 3: Start gesture detection
        self.start_gesture_detection()
        
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
        sys.exit(1)


if __name__ == "__main__":
    main()
