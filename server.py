"""
server.py

Flask-based server that:
- Serves the pages (camera client and viewer)
- Accepts POSTed JPEG frames at /upload
- Exposes an MJPEG stream at /stream

Run:
    pip install flask
    python server.py

Open on any device in same Wi-Fi:
- Camera client: http://<server-ip>:5000/camera
- Viewer:        http://<server-ip>:5000/viewer
- Raw MJPEG:     http://<server-ip>:5000/stream
"""

from flask import Flask, Response, request, send_from_directory, render_template_string
import threading
import time

app = Flask(__name__)

# Shared state: latest JPEG bytes and lock
latest_frame = {"data": None, "time": 0.0}
frame_lock = threading.Lock()

BOUNDARY = "--frameboundary"

# ------- Pages served directly (simple templates) -------

CAMERA_PAGE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Camera Client — Upload frames</title>
  <style>
    body {
      font-family: system-ui, Segoe UI, Roboto, Arial;
      background: #fafafa;
      padding: 20px;
    }
    video, img{
      max-width:100%;
      border-radius:8px;
      border:1px solid #ddd
    }
    #controls{
      margin-top:8px
    }
    h2 { margin-bottom: 10px; }
    video {
      max-width: 100%;
      border-radius: 8px;
      border: 1px solid #ccc;
      background: #000;
    }
    #controls {
      margin-top: 12px;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    label {
      background: white;
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid #ddd;
    }
    button {
      padding: 10px 16px;
      border-radius: 6px;
      border: none;
      background: #1976d2;
      color: white;
      font-size: 15px;
      cursor: pointer;
    }
    button:disabled {
      background: #999;
      cursor: not-allowed;
    }
    code {
      background: #eee;
      padding: 3px 6px;
      border-radius: 4px;
    }
  </style>
</head>
<body>
  <h2>Camera → Server (uploading frames)</h2>
  <video id="video" autoplay playsinline muted></video>
  <div id="controls">
    <label>FPS: <input id="fps" value="5" type="number" min="1" max="30"></label>
    <label>Quality (0.1 - 1.0): <input id="quality" value="0.7" step="0.1" min="0.1" max="1"></label>
    <button id="start">Start</button>
    <button id="stop" disabled>Stop</button>
  </div>
  <p>Viewer URL: <code id="viewerUrl">loading…</code></p>
  <script>
  (async () => {
    const video = document.getElementById('video');
    const startBtn = document.getElementById('start');
    const stopBtn = document.getElementById('stop');
    const fpsInput = document.getElementById('fps');
    const qualityInput = document.getElementById('quality');
    const viewerUrlEl = document.getElementById('viewerUrl');

    // show viewer link (same host)
    viewerUrlEl.textContent = location.origin + '/viewer';

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      video.srcObject = stream;
    } catch (e) {
      alert('Camera error: ' + e.message);
      return;
    }

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    let running = false;
    let loopHandle = null;

    function sendFrameBlob(blob) {
      // send via fetch POST as binary
      fetch('/upload', {
        method: 'POST',
        headers: {'Content-Type': 'image/jpeg'},
        body: blob
      }).catch(err => console.warn('Upload error', err));
    }

    async function captureOnce() {
      if (!video.videoWidth || !video.videoHeight) return;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);
      // convert to blob (jpeg)
      const quality = parseFloat(qualityInput.value) || 0.7;
      canvas.toBlob((blob) => {
        if (blob) sendFrameBlob(blob);
      }, 'image/jpeg', quality);
    }

    function startLoop() {
      if (running) return;
      running = true;
      const fps = Math.max(1, parseInt(fpsInput.value) || 5);
      const interval = 1000 / fps;
      loopHandle = setInterval(captureOnce, interval);
      startBtn.disabled = true;
      stopBtn.disabled = false;
    }

    function stopLoop() {
      running = false;
      if (loopHandle) { clearInterval(loopHandle); loopHandle = null; }
      startBtn.disabled = false;
      stopBtn.disabled = true;
    }

    startBtn.onclick = startLoop;
    stopBtn.onclick = stopLoop;

    // optional: start automatically
    // startLoop();
  })();
  </script>
</body>
</html>
"""

VIEWER_PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Viewer</title>
  <style>
    body {
      font-family: system-ui, Segoe UI, Roboto, Arial;
      background: #f5f5f5;
      padding: 20px;
    }
    h2 { margin-bottom: 10px; }
    img {
      max-width: 100%;
      border-radius: 8px;
      border: 1px solid #ccc;
      display: block;
      background: #000;
    }
    .controls {
      margin: 15px 0;
      display: flex;
      gap: 10px;
    }
    button {
      padding: 10px 16px;
      border-radius: 6px;
      border: none;
      cursor: pointer;
      background: #1976d2;
      color: white;
      font-size: 15px;
    }
    button:disabled {
      background: #999;
      cursor: not-allowed;
    }
  </style>
</head>
<body>

  <h2>Viewer</h2>
  <p>Raw stream for other devices: <code>/stream</code></p>

  <div class="controls">
    <button id="startRec">Start Recording</button>
    <button id="stopRec" disabled>Stop & Save</button>
  </div>

  <img id="mjpeg" src="/stream" alt="Live Stream">

  <script>
    const img = document.getElementById("mjpeg");
    const startBtn = document.getElementById("startRec");
    const stopBtn = document.getElementById("stopRec");

    let canvas, ctx, recorder, chunks = [];

    function createCanvas() {
      canvas = document.createElement("canvas");
      canvas.width = img.clientWidth;
      canvas.height = img.clientHeight;
      ctx = canvas.getContext("2d");
    }

    function drawFrame() {
      if (!canvas || !ctx) return;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      requestAnimationFrame(drawFrame);
    }

    startBtn.onclick = () => {
      createCanvas();
      drawFrame();

      const stream = canvas.captureStream(30);
      recorder = new MediaRecorder(stream);

      recorder.ondataavailable = e => chunks.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: "video/webm" });
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = "recorded_video.webm";
        a.click();

        chunks = [];
      };

      recorder.start();
      startBtn.disabled = true;
      stopBtn.disabled = false;
    };

    stopBtn.onclick = () => {
      recorder.stop();
      startBtn.disabled = false;
      stopBtn.disabled = true;
    };
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return """<p>Server running. Use <a href="/camera">/camera</a> (send frames) or <a href="/viewer">/viewer</a> (watch).</p>"""

@app.route('/camera')
def camera_page():
    return render_template_string(CAMERA_PAGE)

@app.route('/viewer')
def viewer_page():
    return render_template_string(VIEWER_PAGE)

# ------- Upload endpoint: camera client POSTs JPEG bytes here -------
@app.route('/upload', methods=['POST'])
def upload_frame():
    # Expect raw JPEG bytes in request.data
    data = request.get_data()
    if not data:
        return ('no data', 400)
    with frame_lock:
        latest_frame['data'] = data
        latest_frame['time'] = time.time()
    return ('ok', 200)

# ------- MJPEG stream: multipart/x-mixed-replace -------
def mjpeg_generator():
    # Send frames as they arrive. If none yet, send a small heartbeat image
    last_sent_ts = 0.0
    heartbeat = None
    while True:
        with frame_lock:
            data = latest_frame.get('data')
            ts = latest_frame.get('time', 0.0)
        if data is not None and ts != last_sent_ts:
            last_sent_ts = ts
            # yield multipart frame
            yield (b'--frameboundary\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + f"{len(data)}".encode() + b'\r\n\r\n' + data + b'\r\n')
        else:
            # no new frame; wait a short while to avoid busy loop
            time.sleep(0.05)
            # optionally continue to the top
            continue

@app.route('/stream')
def stream():
    # Note: browsers will render <img src="/stream"> as MJPEG automatically
    return Response(mjpeg_generator(),
                    mimetype='multipart/x-mixed-replace; boundary=frameboundary')

# Static files (if needed)
@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    print("Starting server on http://0.0.0.0:5000")
    print("Camera client -> POST frames to /upload (camera page at /camera)")
    print("Viewer -> open /viewer or use /stream directly in other devices")
    app.run(host='0.0.0.0', port=5000, threaded=True)