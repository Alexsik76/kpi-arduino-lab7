import cv2
import logging
from flask import Flask, Response
from core import TrackingSystem

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

app = Flask(__name__)
system = TrackingSystem()

def generate_mjpeg():
    """Generates MJPEG stream for the browser."""
    while True:
        frame = system.get_frame()
        if frame is None:
            continue
            
        (flag, encodedImage) = cv2.imencode(".jpg", frame)
        if not flag: continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

@app.route("/")
def index():
    return """
    <html>
        <body style="background: #111; color: white; text-align: center;">
            <h2>PID Tracking System</h2>
            <img src="/video_feed" style="border: 2px solid green; width: 640px;">
        </body>
    </html>
    """

@app.route("/video_feed")
def video_feed():
    return Response(generate_mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    try:
        system.start()
        # Disable reloader to prevent double initialization of hardware
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    finally:
        system.stop()