"""
Configuration file for Hand Gesture-Based File Transfer System
Contains all network settings, gesture thresholds, and system parameters
"""

# Network Configuration
UDP_PORT = 37020  # Port for device discovery broadcasts
TCP_PORT = 37021  # Port for file transfer
BROADCAST_INTERVAL = 2  # Seconds between broadcast messages
BUFFER_SIZE = 4096  # File transfer buffer size (4KB chunks)
DISCOVERY_TIMEOUT = 10  # Seconds to wait for receiver discovery

# Gesture Detection Configuration
PINCH_THRESHOLD = 0.05  # Distance threshold for pinch detection (normalized)
GESTURE_HOLD_TIME = 0.5  # Seconds to hold gesture before triggering
CONFIDENCE_THRESHOLD = 0.7  # Minimum hand detection confidence

# Camera Configuration
CAMERA_INDEX = 0  # Default webcam index
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
FPS_TARGET = 30

# File Transfer Configuration
RECEIVED_FILES_DIR = "received_files"  # Directory to save received files
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB maximum file size

# Visual Feedback Colors (BGR format for OpenCV)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)
COLOR_BLUE = (255, 0, 0)
COLOR_YELLOW = (0, 255, 255)
COLOR_WHITE = (255, 255, 255)
