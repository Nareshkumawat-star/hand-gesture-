# Hand Gesture-Based File Transfer System

A wireless file transfer system inspired by Xiaomi's gesture sharing feature. Transfer files between two laptops using hand gestures detected via webcam, with automatic device discovery over Wi-Fi.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)

## 🌟 Features

- **Real-time Hand Gesture Recognition**: Uses MediaPipe to detect pinch gestures (thumb + index finger)
- **Automatic Device Discovery**: No need to manually enter IP addresses - devices find each other automatically via UDP broadcast
- **Reliable File Transfer**: TCP sockets ensure files are transferred completely and correctly
- **User-Friendly Interface**: Visual feedback with hand tracking overlay and transfer status
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Lightweight**: Minimal dependencies, easy to set up

## 📁 Project Structure

```
hand gesture/
├── sender.py           # Sender application with gesture detection
├── receiver.py         # Receiver application with auto-discovery
├── gesture_detector.py # Hand gesture recognition module
├── network_utils.py    # Device discovery and file transfer utilities
├── config.py          # Configuration constants
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## 🔧 Installation

### Prerequisites

- Python 3.8 or higher
- Webcam
- Two laptops connected to the same Wi-Fi network

### Setup Instructions

1. **Clone or download this project** to both laptops

2. **Install Python dependencies** on both laptops:

```bash
cd "hand gesture"
pip install -r requirements.txt
```

> **Note**: If you encounter issues installing MediaPipe on Windows, you may need to install Visual C++ Redistributable.

## 🚀 Usage

### Step 1: Start the Receiver (Laptop A)

On the laptop that will **receive** files:

```bash
python receiver.py
```

You should see:
```
HAND GESTURE FILE RECEIVER
Device Name: File Receiver
Local IP: 192.168.x.x
Received files will be saved to: received_files/

WAITING FOR FILES...
```

Keep this running. It will automatically broadcast its presence on the network.

### Step 2: Start the Sender (Laptop B)

On the laptop that will **send** files:

```bash
python sender.py
```

The application will guide you through:

1. **File Selection**: A dialog will open - select the file you want to transfer
2. **Device Discovery**: The app will automatically find the receiver (wait ~10 seconds)
3. **Gesture Detection**: Your webcam will open showing a live feed

### Step 3: Perform the Gesture

1. Show your hand to the camera
2. Make a **pinch gesture** by touching your thumb and index finger together
3. Hold the gesture for **0.5 seconds**
4. The file will automatically transfer!

### Controls

**Sender Application:**
- `q` - Quit the application
- `n` - Select a new file to send (after successful transfer)

**Receiver Application:**
- `Ctrl+C` - Stop the receiver

## 🎯 How It Works

### Architecture Overview

```
┌─────────────────┐                    ┌─────────────────┐
│   SENDER        │                    │   RECEIVER      │
│   (Laptop B)    │                    │   (Laptop A)    │
├─────────────────┤                    ├─────────────────┤
│                 │                    │                 │
│ 1. Webcam       │                    │ 1. UDP Broadcast│
│    ↓            │                    │    (Announce)   │
│ 2. MediaPipe    │   UDP Discovery    │    ↓            │
│    Hand Track   │◄───────────────────┤ 2. TCP Server   │
│    ↓            │                    │    (Listen)     │
│ 3. Pinch Detect │                    │                 │
│    ↓            │                    │                 │
│ 4. TCP Client   │   File Transfer    │                 │
│    (Send File)  ├───────────────────►│ 3. Save File    │
│                 │                    │                 │
└─────────────────┘                    └─────────────────┘
```

### Technical Details

1. **Gesture Detection** (`gesture_detector.py`):
   - Uses MediaPipe Hands to detect 21 hand landmarks
   - Calculates Euclidean distance between thumb tip and index finger tip
   - Triggers when distance < 0.05 (normalized) for 0.5 seconds

2. **Device Discovery** (`network_utils.py`):
   - Receiver broadcasts UDP packets on port 37020 every 2 seconds
   - Sender listens for broadcasts to discover receiver's IP address
   - No manual IP configuration needed!

3. **File Transfer** (`network_utils.py`):
   - TCP connection on port 37021 for reliable transfer
   - Sends file metadata (name, size) first
   - Transfers file in 4KB chunks with progress display
   - Handles duplicate filenames automatically

## ⚙️ Configuration

You can customize settings in `config.py`:

```python
# Network ports
UDP_PORT = 37020  # Device discovery
TCP_PORT = 37021  # File transfer

# Gesture sensitivity
PINCH_THRESHOLD = 0.05  # Lower = more sensitive
GESTURE_HOLD_TIME = 0.5  # Seconds to hold gesture

# Camera settings
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
```

## 🐛 Troubleshooting

### Receiver not found

- **Check Wi-Fi**: Both laptops must be on the same network
- **Firewall**: Allow Python through firewall on both laptops
- **Ports**: Ensure ports 37020 and 37021 are not blocked
- **Wait longer**: Discovery can take up to 10 seconds

### Camera not working

- **Permissions**: Grant camera access to Python/Terminal
- **Camera index**: Try changing `CAMERA_INDEX` in `config.py` (0, 1, or 2)
- **Other apps**: Close other apps using the webcam

### Gesture not detected

- **Lighting**: Ensure good lighting conditions
- **Hand position**: Keep hand clearly visible in frame
- **Distance**: Keep hand at medium distance from camera
- **Sensitivity**: Adjust `PINCH_THRESHOLD` in `config.py`

### File transfer fails

- **Network stability**: Ensure stable Wi-Fi connection
- **File size**: Very large files may take time
- **Disk space**: Ensure receiver has enough disk space

## 📚 Academic Context

This project demonstrates key concepts in:

- **Computer Vision**: Real-time hand tracking and gesture recognition
- **Networking**: UDP broadcasting, TCP sockets, client-server architecture
- **Human-Computer Interaction**: Natural gesture-based interfaces
- **Distributed Systems**: Device discovery and peer-to-peer communication

Perfect for final-year projects in Computer Science, showcasing practical applications of theoretical concepts.

## 🔒 Security Note

This system is designed for trusted local networks (home/office Wi-Fi). For production use, consider adding:
- Authentication mechanisms
- Encryption for file transfer
- User confirmation before receiving files

## 📝 License

This project is open-source and available for educational purposes.

## 🤝 Contributing

Feel free to fork, modify, and improve this project for your needs!

## 📧 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all dependencies are installed correctly
3. Ensure both laptops meet the prerequisites

---

**Enjoy wireless file sharing with hand gestures! 👋📁**
