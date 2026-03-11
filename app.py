from flask import Flask, render_template, Response, request, jsonify
from picamera2 import Picamera2
import cv2
import serial
import threading
import json
import os
import time
from datetime import datetime

app = Flask(__name__)

# === CONFIGURATION ===
PIN_CODE = "1234"
DATA_FILE = "data.json"
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 9600

# === STATE ===
system_active = False
servo_mode = "auto"       # "auto" ou "manual"
servo_position = 90
intrusions = []
authenticated = False
pending_alarm = False

# === SERIAL ===
arduino = None
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("[SERIAL] Arduino connecté")
except Exception as e:
    print(f"[SERIAL] Erreur connexion Arduino: {e}")

# === CAMERA ===
picam2 = Picamera2()
picam2.configure(
    picam2.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"},
        controls={"FrameRate": 20}
    )
)
picam2.start()

# === JSON DATA ===
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"intrusions": [], "settings": {"pin": PIN_CODE}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def log_intrusion():
    data = load_data()
    entry = {
        "id": len(data["intrusions"]) + 1,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "date": datetime.now().strftime("%d/%m/%Y"),
        "time": datetime.now().strftime("%H:%M:%S")
    }
    data["intrusions"].append(entry)
    if len(data["intrusions"]) > 50:
        data["intrusions"] = data["intrusions"][-50:]
    save_data(data)
    intrusions.append(entry)
    return entry

# === SERIAL COMMUNICATION ===
def send_command(cmd):
    global arduino
    if arduino and arduino.is_open:
        try:
            arduino.write((cmd + "\n").encode())
            print(f"[SERIAL] Envoyé: {cmd}")
        except Exception as e:
            print(f"[SERIAL] Erreur envoi: {e}")

def read_serial():
    global arduino, system_active, pending_alarm
    while True:
        if arduino and arduino.is_open:
            try:
                line = arduino.readline().decode("utf-8").strip()
                if line == "INTRUSION" and system_active:
                    pending_alarm = True          # ← ajouter
                    entry = log_intrusion()
                    print(f"[INTRUSION] {entry['timestamp']}")
            except:
                pass
        time.sleep(0.05)

serial_thread = threading.Thread(target=read_serial, daemon=True)
serial_thread.start()

# === CAMERA STREAM ===
def generate_frames():
    global system_active
    while True:
        if system_active:
            frame = picam2.capture_array()
            _, buffer = cv2.imencode(
                ".jpg", frame,
                [cv2.IMWRITE_JPEG_QUALITY, 70]
            )
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n"
                   + buffer.tobytes() + b"\r\n")
        else:
            time.sleep(0.1)

# === ROUTES ===
@app.route("/")
def index():
    data = load_data()
    return render_template("index.html",
                           intrusions=data["intrusions"][-10:][::-1])

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/auth", methods=["POST"])
def auth():
    data = request.get_json()
    pin = data.get("pin", "")
    stored = load_data().get("settings", {}).get("pin", PIN_CODE)
    if pin == stored:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route("/api/system/toggle", methods=["POST"])
def toggle_system():
    global system_active
    data = request.get_json()
    pin = data.get("pin", "")
    stored = load_data().get("settings", {}).get("pin", PIN_CODE)
    if pin != stored:
        return jsonify({"success": False, "message": "PIN incorrect"}), 401

    system_active = not system_active
    if system_active:
        send_command("SYSTEM_ON")
    else:
        send_command("SYSTEM_OFF")
    return jsonify({"success": True, "active": system_active})

@app.route("/api/system/status")
def system_status():
    return jsonify({
        "active": system_active,
        "servo_mode": servo_mode,
        "servo_position": servo_position
    })

@app.route("/api/servo/mode", methods=["POST"])
def set_servo_mode():
    global servo_mode
    data = request.get_json()
    mode = data.get("mode", "auto")
    servo_mode = mode
    if mode == "auto":
        send_command("MODE_AUTO")
    else:
        send_command("MODE_MANUAL")
    return jsonify({"success": True, "mode": servo_mode})

@app.route("/api/servo/move", methods=["POST"])
def move_servo():
    global servo_position
    data = request.get_json()
    direction = data.get("direction", "")
    if direction == "left":
        servo_position = max(0, servo_position - 15)
        send_command("SERVO_LEFT")
    elif direction == "right":
        servo_position = min(180, servo_position + 15)
        send_command("SERVO_RIGHT")
    return jsonify({"success": True, "position": servo_position})

@app.route("/api/intrusions")
def get_intrusions():
    data = load_data()
    return jsonify(data["intrusions"][-20:][::-1])

@app.route("/api/intrusions/clear", methods=["POST"])
def clear_intrusions():
    data = load_data()
    data["intrusions"] = []
    save_data(data)
    intrusions.clear()
    return jsonify({"success": True})

@app.route("/api/alarm/status")
def alarm_status():
    return jsonify({"pending": pending_alarm})

@app.route("/api/alarm/ack", methods=["POST"])
def alarm_ack():
    global pending_alarm
    data = request.get_json()
    action = data.get("action", "")  # "authorities" ou "dismiss"
    pending_alarm = False
    send_command("ALARM_ACK")
    # Logguer l'action
    db = load_data()
    if db["intrusions"]:
        db["intrusions"][-1]["action"] = action
        save_data(db)
    return jsonify({"success": True, "action": action})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)