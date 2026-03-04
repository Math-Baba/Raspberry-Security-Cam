from flask import Flask, render_template, Response, request, jsonify, session, redirect, url_for
from functools import wraps
from datetime import datetime, timezone
from picamera2 import Picamera2
import cv2
import time

from utils.config_store import ConfigStore
from utils.auth import verify_pin, is_valid_pin, hash_pin
from utils.logger import push_log

from services.hardware_controller import on_system_activated, on_system_deactivated

# --------------------------------------------------
# Flask
# --------------------------------------------------

app = Flask(__name__)
app.secret_key = "CHANGE_ME_TO_A_RANDOM_SECRET"

store = ConfigStore("config.json")

# --------------------------------------------------
# Camera Singleton (IMPORTANT 🔥)
# --------------------------------------------------

picam2 = None

def get_camera():
    global picam2

    if picam2 is None:
        picam2 = Picamera2()

        picam2.configure(
            picam2.create_video_configuration(
                main={"size": (640, 480), "format": "RGB888"},
                controls={"FrameRate": 20}
            )
        )

        picam2.start()
        time.sleep(2)  # laisse le driver se stabiliser

    return picam2

# --------------------------------------------------
# Config init
# --------------------------------------------------

def ensure_config_initialized():
    cfg = store.read()

    if not cfg.get("auth", {}).get("pin_hash"):
        cfg.setdefault("auth", {})
        cfg["auth"]["username"] = "admin"
        cfg["auth"]["pin_hash"] = hash_pin("1234")

        cfg.setdefault("system", {})
        cfg["system"]["active"] = True
        cfg["system"]["start_time_iso"] = datetime.now(timezone.utc).isoformat()
        cfg["system"]["last_login_iso"] = None

        push_log(cfg, "PIN initialisé (1234)")
        store.write(cfg)

# --------------------------------------------------
# Auth middleware
# --------------------------------------------------

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

# --------------------------------------------------
# Video streaming
# --------------------------------------------------

def generate_frames():
    while True:
        cfg = store.read()
        if not cfg.get("system", {}).get("active", False):
            time.sleep(0.1)
            continue

        camera = get_camera()
        frame = camera.capture_array()

        ok, buffer = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 70]
        )

        if not ok:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            buffer.tobytes() +
            b"\r\n"
        )

# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.route("/")
def root():
    return redirect(
        url_for("dashboard") if session.get("user") else url_for("login")
    )

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=session.get("user"))

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

# --------------------------------------------------
# API Auth
# --------------------------------------------------

@app.route("/api/login", methods=["POST"])
def api_login():
    ensure_config_initialized()

    data = request.get_json(force=True)

    username = (data.get("username") or "").strip()
    pin = (data.get("pin") or "").strip()

    cfg = store.read()

    expected_user = cfg.get("auth", {}).get("username", "admin")
    pin_hash = cfg.get("auth", {}).get("pin_hash", "")

    if username != expected_user:
        return jsonify({"ok": False}), 401

    if not is_valid_pin(pin) or not verify_pin(pin, pin_hash):
        return jsonify({"ok": False}), 401

    session["user"] = username

    cfg["system"]["last_login_iso"] = datetime.now(timezone.utc).isoformat()

    push_log(cfg, f"Connexion admin: {username}")
    store.write(cfg)

    return jsonify({"ok": True})

# --------------------------------------------------
# Video stream endpoint
# --------------------------------------------------

@app.route("/video_feed")
@login_required
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

# --------------------------------------------------
# Status
# --------------------------------------------------

@app.route("/api/status")
@login_required
def api_status():
    cfg = store.read()
    sys_cfg = cfg.get("system", {})

    start_iso = sys_cfg.get("start_time_iso")
    last_login = sys_cfg.get("last_login_iso")

    uptime_s = None

    try:
        if start_iso:
            start = datetime.fromisoformat(
                start_iso.replace("Z", "+00:00")
            )
            uptime_s = int(
                (datetime.now(timezone.utc) - start).total_seconds()
            )
    except:
        uptime_s = None

    return jsonify({
        "ok": True,
        "active": sys_cfg.get("active", False),
        "uptime_s": uptime_s,
        "last_login_iso": last_login,
        "logs": cfg.get("logs", [])[:8]
    })

# --------------------------------------------------
# Toggle system
# --------------------------------------------------

@app.route("/api/toggle", methods=["POST"])
@login_required
def api_toggle():
    data = request.get_json(force=True)

    pin = (data.get("pin") or "").strip()
    target = data.get("target")

    cfg = store.read()
    pin_hash = cfg.get("auth", {}).get("pin_hash", "")

    if not is_valid_pin(pin) or not verify_pin(pin, pin_hash):
        return jsonify({"ok": False}), 403

    if not isinstance(target, bool):
        return jsonify({"ok": False}), 400

    current = cfg["system"].get("active", False)

    if current == target:
        return jsonify({"ok": True, "active": current})

    cfg["system"]["active"] = target

    if target:
        push_log(cfg, "Système activé")
        on_system_activated()
    else:
        push_log(cfg, "Système désactivé")
        on_system_deactivated()

    store.write(cfg)

    return jsonify({"ok": True, "active": target})

# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    ensure_config_initialized()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )