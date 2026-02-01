"""
Hand Gesture Detection Module
Uses MediaPipe to detect hand landmarks and recognize pinch/open pinch gestures
"""

import cv2
import mediapipe as mp
import numpy as np
import time
from config import PINCH_THRESHOLD, GESTURE_HOLD_TIME, CONFIDENCE_THRESHOLD
from config import COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_YELLOW, OPEN_PINCH_THRESHOLD


class GestureDetector:
    """Detects hand gestures using MediaPipe Hands"""
    
    def __init__(self):
        """Initialize MediaPipe Hands model"""
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=CONFIDENCE_THRESHOLD,
            min_tracking_confidence=CONFIDENCE_THRESHOLD
        )
        
        # Gesture state tracking
        self.pinch_start_time = None
        self.is_pinching = False
        self.gesture_triggered = False
        
        # Open pinch state tracking
        self.open_pinch_start_time = None
        self.open_pinch_triggered = False
        
    def calculate_distance(self, point1, point2):
        """
        Calculate Euclidean distance between two points
        
        Args:
            point1: First landmark point (x, y, z)
            point2: Second landmark point (x, y, z)
            
        Returns:
            float: Distance between points
        """
        return np.sqrt(
            (point1.x - point2.x) ** 2 +
            (point1.y - point2.y) ** 2 +
            (point1.z - point2.z) ** 2
        )
    
    def detect_pinch(self, hand_landmarks):
        """
        Detect pinch gesture (thumb tip touching index finger tip)
        
        Args:
            hand_landmarks: MediaPipe hand landmarks
            
        Returns:
            bool: True if pinch detected, False otherwise
        """
        # Get thumb tip and index finger tip landmarks
        thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        
        # Calculate distance between thumb and index finger
        distance = self.calculate_distance(thumb_tip, index_tip)
        
        return distance < PINCH_THRESHOLD
    
    def detect_open_pinch(self, hand_landmarks):
        """
        Detect open pinch gesture (thumb and index finger spread apart)
        
        Args:
            hand_landmarks: MediaPipe hand landmarks
            
        Returns:
            bool: True if open pinch detected, False otherwise
        """
        # Get thumb tip and index finger tip landmarks
        thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        
        # Calculate distance between thumb and index finger
        distance = self.calculate_distance(thumb_tip, index_tip)
        
        # Open pinch = fingers spread apart
        return distance > OPEN_PINCH_THRESHOLD
    
    def process_frame(self, frame):
        """
        Process a video frame to detect pinch gesture (for sender)
        
        Args:
            frame: OpenCV frame (BGR image)
            
        Returns:
            tuple: (processed_frame, gesture_detected)
                - processed_frame: Frame with hand landmarks drawn
                - gesture_detected: True if pinch gesture completed
        """
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.hands.process(rgb_frame)
        
        gesture_detected = False
        status_text = "No hand detected"
        status_color = COLOR_RED
        
        # Check if hand is detected
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=COLOR_GREEN, thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=COLOR_BLUE, thickness=2)
                )
                
                # Detect pinch gesture
                is_pinching_now = self.detect_pinch(hand_landmarks)
                
                if is_pinching_now:
                    # Start timing the pinch
                    if self.pinch_start_time is None:
                        self.pinch_start_time = time.time()
                    
                    # Check if pinch held long enough
                    hold_duration = time.time() - self.pinch_start_time
                    
                    if hold_duration >= GESTURE_HOLD_TIME and not self.gesture_triggered:
                        # Gesture completed!
                        gesture_detected = True
                        self.gesture_triggered = True
                        status_text = "GESTURE TRIGGERED!"
                        status_color = COLOR_YELLOW
                    else:
                        # Still holding
                        progress = int((hold_duration / GESTURE_HOLD_TIME) * 100)
                        status_text = f"Pinching... {progress}%"
                        status_color = COLOR_GREEN
                else:
                    # Reset if pinch released
                    self.pinch_start_time = None
                    if self.gesture_triggered:
                        status_text = "Gesture completed - Ready for next"
                        status_color = COLOR_BLUE
                    else:
                        status_text = "Hand detected - Make pinch gesture"
                        status_color = COLOR_GREEN
        else:
            # No hand detected - reset state
            self.pinch_start_time = None
            self.gesture_triggered = False
        
        # Draw status text on frame
        cv2.putText(
            frame,
            status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            status_color,
            2,
            cv2.LINE_AA
        )
        
        # Draw progress bar when pinching
        if self.pinch_start_time is not None and not self.gesture_triggered:
            hold_duration = time.time() - self.pinch_start_time
            progress = min(hold_duration / GESTURE_HOLD_TIME, 1.0)
            
            # Progress bar dimensions
            bar_x = 10
            bar_y = 50
            bar_width = 300
            bar_height = 30
            
            # Draw background (gray)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
            
            # Draw progress (green gradient)
            fill_width = int(bar_width * progress)
            if fill_width > 0:
                # Color transitions from yellow to green as progress increases
                green = int(255 * progress)
                blue = 0
                red = int(255 * (1 - progress))
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), (blue, green, red), -1)
            
            # Draw border
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 2)
            
            # Draw percentage text on bar
            percent_text = f"{int(progress * 100)}%"
            text_size = cv2.getTextSize(percent_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            text_x = bar_x + (bar_width - text_size[0]) // 2
            text_y = bar_y + (bar_height + text_size[1]) // 2
            cv2.putText(frame, percent_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame, gesture_detected
    
    def process_frame_open_pinch(self, frame, pending_info=None):
        """
        Process a video frame to detect open pinch gesture (for receiver)
        
        Args:
            frame: OpenCV frame (BGR image)
            pending_info: Optional dict with file info to display
            
        Returns:
            tuple: (processed_frame, gesture_detected)
                - processed_frame: Frame with hand landmarks drawn
                - gesture_detected: True if open pinch gesture completed
        """
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.hands.process(rgb_frame)
        
        gesture_detected = False
        status_text = "No hand detected - Show open hand"
        status_color = COLOR_RED
        
        # Check if hand is detected
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=COLOR_GREEN, thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=COLOR_BLUE, thickness=2)
                )
                
                # Detect open pinch gesture
                is_open_pinch_now = self.detect_open_pinch(hand_landmarks)
                
                if is_open_pinch_now:
                    # Start timing the open pinch
                    if self.open_pinch_start_time is None:
                        self.open_pinch_start_time = time.time()
                    
                    # Check if open pinch held long enough
                    hold_duration = time.time() - self.open_pinch_start_time
                    
                    if hold_duration >= GESTURE_HOLD_TIME and not self.open_pinch_triggered:
                        # Gesture completed!
                        gesture_detected = True
                        self.open_pinch_triggered = True
                        status_text = "ACCEPTING FILE!"
                        status_color = COLOR_YELLOW
                    else:
                        # Still holding
                        progress = int((hold_duration / GESTURE_HOLD_TIME) * 100)
                        status_text = f"Open pinch... {progress}%"
                        status_color = COLOR_GREEN
                else:
                    # Reset if open pinch released
                    self.open_pinch_start_time = None
                    if self.open_pinch_triggered:
                        status_text = "File accepted!"
                        status_color = COLOR_BLUE
                    else:
                        status_text = "Spread thumb & index to accept"
                        status_color = COLOR_GREEN
        else:
            # No hand detected - reset state
            self.open_pinch_start_time = None
            self.open_pinch_triggered = False
        
        # Draw status text on frame
        cv2.putText(
            frame,
            status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            status_color,
            2,
            cv2.LINE_AA
        )
        
        # Draw pending file info if provided
        if pending_info:
            cv2.putText(
                frame,
                f"Incoming: {pending_info.get('file_name', 'Unknown')}",
                (10, frame.shape[0] - 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
            cv2.putText(
                frame,
                f"From: {pending_info.get('sender_ip', 'Unknown')}",
                (10, frame.shape[0] - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
        
        # Draw progress bar when doing open pinch
        if self.open_pinch_start_time is not None and not self.open_pinch_triggered:
            hold_duration = time.time() - self.open_pinch_start_time
            progress = min(hold_duration / GESTURE_HOLD_TIME, 1.0)
            
            # Progress bar dimensions
            bar_x = 10
            bar_y = 50
            bar_width = 300
            bar_height = 30
            
            # Draw background (gray)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
            
            # Draw progress (green gradient)
            fill_width = int(bar_width * progress)
            if fill_width > 0:
                green = int(255 * progress)
                blue = 0
                red = int(255 * (1 - progress))
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), (blue, green, red), -1)
            
            # Draw border
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 2)
            
            # Draw percentage text
            percent_text = f"{int(progress * 100)}%"
            text_size = cv2.getTextSize(percent_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            text_x = bar_x + (bar_width - text_size[0]) // 2
            text_y = bar_y + (bar_height + text_size[1]) // 2
            cv2.putText(frame, percent_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame, gesture_detected
    
    def reset_gesture(self):
        """Reset gesture state to allow new gesture detection"""
        self.gesture_triggered = False
        self.pinch_start_time = None
    
    def reset_open_pinch(self):
        """Reset open pinch state"""
        self.open_pinch_triggered = False
        self.open_pinch_start_time = None
    
    def cleanup(self):
        """Release MediaPipe resources"""
        self.hands.close()
