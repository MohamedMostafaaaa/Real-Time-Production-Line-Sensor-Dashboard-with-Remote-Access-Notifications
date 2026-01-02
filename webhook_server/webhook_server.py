from __future__ import annotations

import os
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from webhook_server import Flask, request, render_template, redirect, url_for, session
from flask.json import jsonify


def _resource_path(rel: str) -> Path:
    """
    Resolve resource paths in both development and PyInstaller frozen mode.

    - In dev: resources are on disk next to this file.
    - In frozen: bundled files live under sys._MEIPASS.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / rel


# Load .env from EXE directory (so it stays editable in production)
EXE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
load_dotenv(EXE_DIR / ".env")

# Templates are bundled inside the executable (sys._MEIPASS)
TEMPLATES_DIR = _resource_path("templates")

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))

UI_USER = os.getenv("WEB_UI_USER", "admin")
UI_PASS = os.getenv("WEB_UI_PASS", "admin")
EXPECTED_TOKEN = os.getenv("WEBHOOK_TOKEN", "dev-token")
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-change-me")

EVENTS: list[dict] = []


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def require_login(fn):
    """Browser-only pages: must be logged in (session)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("auth") is True:
            return fn(*args, **kwargs)
        return redirect(url_for("login"))
    return wrapper


def require_bearer_or_session(fn):
    """API pages: allow either browser session OR Bearer token."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("auth") is True:
            return fn(*args, **kwargs)

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.removeprefix("Bearer ").strip()
            if token == EXPECTED_TOKEN:
                return fn(*args, **kwargs)
            return jsonify({"error": "invalid token"}), 403

        return jsonify({"error": "unauthorized"}), 401
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == UI_USER and p == UI_PASS:
            session["auth"] = True
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid username/password")
    return render_template("login.html", error=None)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@require_login
def index():
    return render_template("index.html")


@app.post("/alarm")
@require_bearer_or_session
def alarm():
    data = request.get_json(silent=True) or {}

    EVENTS.append({"received_at": _now_iso(), "body": data})
    if len(EVENTS) > 500:
        del EVENTS[:-500]

    print("\n=== WEBHOOK RECEIVED ===")
    print(data)

    return jsonify({"status": "ok"}), 200


@app.get("/api/alarm/recent")
@require_bearer_or_session
def api_recent():
    recent = list(reversed(EVENTS[-200:]))
    return jsonify({"count": len(EVENTS), "events": recent}), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # IMPORTANT for EXE: do NOT use debug=True in production
    app.run(host="0.0.0.0", port=8000, debug=False)
