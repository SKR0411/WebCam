from flask import Flask, Response, request, render_template
import threading
import time

app = Flask(__name__)

latest_frame = {"data": None, "time": 0.0}
frame_lock = threading.Lock()

BOUNDARY = "--frameboundary"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/camera")
def camera_page():
    return render_template("camera.html")


@app.route("/viewer")
def viewer_page():
    return render_template("viewer.html")


@app.route("/upload", methods=["POST"])
def upload_frame():
    #new
    frame = request.files.get("frame")
    fps = request.form.get("fps")
    quality = request.form.get("quality")
    width = request.form.get("width")
    height = request.form.get("height")
    
    if not frame:
        return ("no frame", 400)
    
    jpg_bytes = frame.read()
    
    with frame_lock:
        latest_frame["data"] = jpg_bytes
        latest_frame["time"] = time.time()
        latest_frame["fps"] = fps
        latest_frame["quality"] = quality
        latest_frame["width"] = width
        latest_frame["height"] = height
    
    return ("ok", 200)
    #end

def mjpeg_generator():
    last = 0
    while True:
        with frame_lock:
            frame = latest_frame["data"]
            ts = latest_frame["time"]

        if frame and ts != last:
            last = ts
            #old
            '''yield (
                b"--frameboundary\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                frame + b"\r\n"
            )'''
            #new
            yield (
                b"--frameboundary\r\n"
                b"Content-Type: image/jpeg\r\n" +
                f"X-FPS: {latest_frame.get('fps')}\r\n".encode() +
                f"X-QUALITY: {latest_frame.get('quality')}\r\n".encode() +
                f"X-RES: {latest_frame.get('width')}x{latest_frame.get('height')}\r\n\r\n".encode() +
                frame + b"\r\n"
            )
            #end
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