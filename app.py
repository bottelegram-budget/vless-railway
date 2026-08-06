#!/usr/bin/env python3
import json
import os
import re
import signal
import subprocess
import time
import uuid as uuidlib
from urllib.parse import quote

from flask import Flask, jsonify, request, send_from_directory, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "peers.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
XRAY_BIN = "/usr/local/bin/xray"
XRAY_PID_FILE = "/tmp/xray.pid"
XRAY_WS_PORT = 8080
XRAY_API_PORT = 10085

app = Flask(__name__, static_folder="static", static_url_path="/static")

UUID_ENV = os.environ.get("UUID", "")
WS_PATH = os.environ.get("WS_PATH", "/ws")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
PORT = os.environ.get("PORT", "443")

# Railway provides the public domain as RAILWAY_PUBLIC_DOMAIN or RAILWAY_STATIC_URL
PUBLIC_DOMAIN = os.environ.get(
    "PUBLIC_DOMAIN",
    os.environ.get("RAILWAY_PUBLIC_DOMAIN", os.environ.get("RAILWAY_STATIC_URL", "localhost")),
)


def load_peers():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    peers = []
    if UUID_ENV:
        peers.append({"name": "main", "id": UUID_ENV, "created": int(time.time())})
    save_peers(peers)
    return peers


def save_peers(peers):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(peers, f, indent=2)


def gen_config():
    peers = load_peers()
    clients = [{"id": p["id"], "email": p["id"], "flow": ""} for p in peers]
    with open(os.path.join(BASE_DIR, "config.template.json")) as f:
        tpl = f.read()
    cfg = tpl.replace("${CLIENTS}", json.dumps(clients)).replace("${WS_PATH}", WS_PATH)
    with open(CONFIG_FILE, "w") as f:
        f.write(cfg)


def reload_xray():
    try:
        with open(XRAY_PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGHUP)
    except Exception:
        pass


def fetch_stats():
    """Query Xray API for per-user traffic (JSON output)."""
    try:
        out = subprocess.run(
            [XRAY_BIN, "api", "statsquery", "--server=127.0.0.1:%d" % XRAY_API_PORT, "-pattern", "user>>>"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        data = json.loads(out)
    except Exception:
        return {}
    stats = {}
    for item in data.get("stat", []):
        m = re.match(r"user>>>(.+)>>>traffic>>>(uplink|downlink)", item.get("name", ""))
        if not m:
            continue
        email, direction = m.group(1), m.group(2)
        try:
            value = int(item.get("value", 0))
        except (TypeError, ValueError):
            value = 0
        stats.setdefault(email, {"uplink": 0, "downlink": 0})
        stats[email][direction] = value
    return stats


def fetch_online():
    """Query Xray API for currently connected user emails."""
    try:
        out = subprocess.run(
            [XRAY_BIN, "api", "statsgetallonlineusers", "--server=127.0.0.1:%d" % XRAY_API_PORT],
            capture_output=True, text=True, timeout=10,
        ).stdout
        data = json.loads(out)
    except Exception:
        return set()
    return set(data.get("users", []))


def share_link(peer_id):
    path = quote(WS_PATH) if WS_PATH else "/"
    return (
        f"vless://{peer_id}@{PUBLIC_DOMAIN}:443?encryption=none&security=tls"
        f"&type=ws&host={PUBLIC_DOMAIN}&path={path}#vless-railway"
    )


def check_auth():
    return ADMIN_TOKEN and request.headers.get("X-Auth-Token") == ADMIN_TOKEN


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/info")
def api_info():
    return jsonify({
        "domain": PUBLIC_DOMAIN,
        "port": 443,
        "ws_path": WS_PATH,
        "share_example": share_link(UUID_ENV or "UUID_PLACEHOLDER"),
    })


@app.route("/api/peers")
def api_peers():
    if not check_auth():
        return jsonify({"error": "unauthorized"}), 401
    stats = fetch_stats()
    online = fetch_online()
    peers = []
    for p in load_peers():
        s = stats.get(p["id"], {"uplink": 0, "downlink": 0})
        peers.append({
            "id": p["id"],
            "name": p.get("name", ""),
            "created": p.get("created", 0),
            "uplink": s["uplink"],
            "downlink": s["downlink"],
            "active": (s["uplink"] + s["downlink"]) > 0,
            "online": p["id"] in online,
            "share": share_link(p["id"]),
        })
    return jsonify(peers)


@app.route("/api/peers", methods=["POST"])
def api_peers_create():
    if not check_auth():
        return jsonify({"error": "unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip() or "peer-%d" % (len(load_peers()) + 1)
    peer = {"name": name, "id": str(uuidlib.uuid4()), "created": int(time.time())}
    peers = load_peers()
    peers.append(peer)
    save_peers(peers)
    gen_config()
    reload_xray()
    return jsonify({"id": peer["id"], "name": peer["name"], "share": share_link(peer["id"])})


@app.route("/api/peers/<peer_id>", methods=["DELETE"])
def api_peers_delete(peer_id):
    if not check_auth():
        return jsonify({"error": "unauthorized"}), 401
    peers = load_peers()
    peers = [p for p in peers if p["id"] != peer_id]
    if not peers:
        return jsonify({"error": "cannot delete last peer"}), 400
    save_peers(peers)
    gen_config()
    reload_xray()
    return jsonify({"ok": True})


@app.route("/api/qr/<peer_id>")
def api_qr(peer_id):
    import qrcode
    if not check_auth():
        return jsonify({"error": "unauthorized"}), 401
    peers = load_peers()
    if not any(p["id"] == peer_id for p in peers):
        return jsonify({"error": "not found"}), 404
    img = qrcode.make(share_link(peer_id))
    img_bytes = img_to_png(img)
    return Response(img_bytes, mimetype="image/png")


def img_to_png(img):
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@app.route("/api/auth")
def api_auth():
    return jsonify({"ok": check_auth()})


@app.route("/api/dbg/stats")
def api_dbg_stats():
    if not check_auth():
        return jsonify({"error": "unauthorized"}), 401
    res = {}
    for cmd in (
        ["api", "statsquery", "--server=127.0.0.1:%d" % XRAY_API_PORT, "-pattern", "user>>>"],
        ["api", "statsgetallonlineusers", "--server=127.0.0.1:%d" % XRAY_API_PORT],
    ):
        try:
            p = subprocess.run([XRAY_BIN] + cmd, capture_output=True, text=True, timeout=10)
            res[" ".join(cmd)] = {"rc": p.returncode, "stdout": p.stdout[:2000], "stderr": p.stderr[:2000]}
        except Exception as e:
            res[" ".join(cmd)] = {"error": str(e)}
    return jsonify(res)


def main():
    import sys
    if "--gen-config" in sys.argv:
        gen_config()
        print("config written to", CONFIG_FILE)
        return
    if not ADMIN_TOKEN:
        print("WARNING: ADMIN_TOKEN not set - dashboard API is unauthenticated!", flush=True)
    app.run(host="0.0.0.0", port=8081, threaded=True)


if __name__ == "__main__":
    main()
