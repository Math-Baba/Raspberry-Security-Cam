from flask import Flask, render_template, Response
from picamera2 import Picamera2
import cv2

app = Flask(__name__)

picam2 = Picamera2()
picam2.configure(
    picam2.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"},
        controls={"FrameRate": 20}
    )
)
picam2.start()

system_active = True


def generate_frames():
    global system_active

    while True:
        if system_active:
            frame = picam2.capture_array()
            _, buffer = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, 70]
            )

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n"
                   + buffer.tobytes() + b"\r\n")


@app.route("/")
def index():
    return render_template("index.html", active=system_active)


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/toggle")
def toggle():
    global system_active
    system_active = not system_active
    return {"active": system_active}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)