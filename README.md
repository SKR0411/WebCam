# WebCam Streaming Server

A lightweight Flask-based webcam system that lets you stream camera frames over your local Wi-Fi. It works on Android (Termux), Windows, Linux and macOS.

---

## Features

- Live camera capture from browser  
- Real-time MJPEG streaming  
- Viewer page for any device on the same network  
- Save frames directly from viewer  
- Clean and responsive UI  
- No external JS libraries  

---

## Folder Structure
```
project/
    ├── server.py 
    ├── README.md 
    └── templates/ 
            ├── index.html
            ├── camera.html 
            └── viewer.html
```
---

## Installation

### 1. Install Python packages

`pip install flask`

### 2. Run the server

`pyton server.py`

### 3. Open in browser

```
http://127.0.0.1:5000/
or
http://Wi-Fi_IP:5000/
```

Find your IP using:

- Termux / Linux: `ifconfig` or `ip addr`
- Windows: `ipconfig`

---

## Endpoints

### GET `/`
Home page of the webcam server.

### GET `/camera`
Opens your device camera and sends frames to backend.

### POST `/upload`
Receives JPEG frames from the camera page.

### GET `/viewer`
Shows the live stream with a save button.

### GET `/stream`
MJPEG stream endpoint used by `/viewer`.

---

## How It Works

1. The browser captures frames using JavaScript.  
2. Frames are converted to JPEG blobs.  
3. Each frame is sent to `/upload`.  
4. The server broadcasts these frames as an MJPEG stream at `/stream`.  
5. Viewer page displays the MJPEG stream in real-time.

---

## Requirements

- Python 3.11 or higher  
- Flask 3.1
- A device with a browser that supports camera access  

---

## Notes

- Works only on local network unless you expose the port using tools like Cloudflared, Ngrok or proper port-forwarding.
- MJPEG is fast but not compressed like video formats.

---

## License

Free for personal and educational use.