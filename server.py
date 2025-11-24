import asyncio
import websockets
import http.server
import socketserver
import threading
import base64

HOST = "0.0.0.0"
PORT = 8000

# ---------------------------
# HTTP server (serves index.html)
# ---------------------------
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=".", **kwargs)

def start_http():
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        print(f"HTTP server running at http://{HOST}:{PORT}")
        httpd.serve_forever()

# ---------------------------
# WebSocket server (receives frames)
# ---------------------------
async def ws_handler(websocket):
    print("Client connected")

    while True:
        try:
            data = await websocket.recv()
            if data.startswith("data:image/jpeg;base64,"):
                img_data = data.split(",")[1]
                img_bytes = base64.b64decode(img_data)

                # Save last frame
                with open("latest.jpg", "wb") as f:
                    f.write(img_bytes)

                print("Frame received and saved as latest.jpg")
        except:
            print("Client disconnected")
            break

async def start_ws():
    print(f"WebSocket server ws://{HOST}:{PORT+1}")
    async with websockets.serve(ws_handler, HOST, PORT + 1):
        await asyncio.Future()

# ---------------------------
# Start both servers
# ---------------------------
threading.Thread(target=start_http, daemon=True).start()
asyncio.run(start_ws())