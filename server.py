from flask import Flask, Response, request, render_template
import threading
import time

app = Flask(__name__)

latest_frame = {"data": None, "time": 0.0}
frame_lock = threading.Lock()

BOUNDARY = "--frameboundary"


@app.route("/")
def index():
    return '<p>Server running. Go to <a href="/camera">/camera</a> or <a href="/viewer">/viewer</a></p>'


@app.route("/camera")
def camera_page():
    return render_template("camera.html")


@app.route("/viewer")
def viewer_page():
    return render_template("viewer.html")


@app.route("/upload", methods=["POST"])
def upload_frame():
    data = request.get_data()
    if not data:
        return ("no data", 400)
    with frame_lock:
        latest_frame["data"] = data
        latest_frame["time"] = time.time()
    return ("ok", 200)


def mjpeg_generator():
    last = 0
    while True:
        with frame_lock:
            frame = latest_frame["data"]
            ts = latest_frame["time"]

        if frame and ts != last:
            last = ts
            yield (
                b"--frameboundary\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                frame + b"\r\n"
            )
        else:
            time.sleep(0.05)


@app.route("/stream")
def stream():
    return Response(
        mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frameboundary",
    )


if __name__ == "__main__":
    print("Server on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)