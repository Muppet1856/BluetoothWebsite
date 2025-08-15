#!/usr/bin/env python3
import os, re, time, atexit, subprocess, hmac, hashlib
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# Default script to run for GitHub webhook events
DEFAULT_WEBHOOK_SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "deploy.sh")
)

# ------------------ Hints for audio devices ------------------
AUDIO_UUID_HINTS = (
    "0000110b",  # A2DP Sink
    "0000110a",  # A2DP Source
    "0000110e",  # AVRCP Target
    "0000110c",  # AVRCP Controller
    "00001108",  # Headset (HSP)
    "0000111e",  # Handsfree (HFP)
)
AUDIO_NAME_HINTS = (
    "bose", "soundlink", "speaker", "headset", "headphone", "airpods",
    "jbl", "sony", "anker", "marshall", "beats", "earbud", "soundcore"
)

# ------------------ Regex ------------------
DEVICE_LINE = re.compile(r"^Device ([0-9A-F:]{17}) (.+)$")
BOOL_LINE   = re.compile(r"^(Paired|Trusted|Connected):\s+(yes|no)$", re.I)
ADAPTER_BOOL= re.compile(r"^(Powered|Discoverable|Pairable|Discovering):\s+(yes|no)$", re.I)

# ------------------ State ------------------
SCAN_STATE = {"wanted": False}
SCAN_PROC  = {"p": None, "adapter": None}
ADAPTER_CACHE = {"mac": None, "ts": 0.0}

# ------------------ Utilities ------------------
def clean_for_js(text: str) -> str:
    """Keep printable plus ANSI escapes, newline and tab for client-side rendering."""
    return "".join(ch for ch in text if ch in ("\n", "\t", "\x1b") or ord(ch) >= 0x20)

def _get_adapter_mac(timeout=10):
    now = time.time()
    if ADAPTER_CACHE["mac"] and now - ADAPTER_CACHE["ts"] < 10:
        return ADAPTER_CACHE["mac"]
    p = subprocess.run(["bluetoothctl", "show"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    out = p.stdout.decode(errors="ignore")
    mac = None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Controller "):
            parts = s.split()
            if len(parts) >= 2:
                mac = parts[1]
                break
    ADAPTER_CACHE["mac"] = mac
    ADAPTER_CACHE["ts"]  = now
    return mac

def run_bctl(cmds, timeout=30):
    """Run bluetoothctl non-interactively with a short script (fresh session)."""
    adapter = _get_adapter_mac()
    prefix = []
    if adapter:
        prefix.append(f"select {adapter}")
    prefix += ["power on"]
    script = "\n".join(prefix + list(cmds) + ["quit"]) + "\n"
    p = subprocess.run(["bluetoothctl"], input=script.encode(),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return p.returncode, p.stdout.decode(errors="ignore"), p.stderr.decode(errors="ignore")

def adapter_status():
    rc, out, _ = run_bctl(["show"])
    st = {"powered": False, "discovering": False, "addr": None, "name": None}
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Controller "):
            parts = s.split()
            st["addr"] = parts[1] if len(parts) > 1 else None
        m = ADAPTER_BOOL.match(s)
        if m:
            key, val = m.group(1).lower(), (m.group(2).lower() == "yes")
            if key == "powered":      st["powered"] = val
            elif key == "discovering":st["discovering"] = val
    return st

def list_devices():
    rc, out, _ = run_bctl(["devices"])
    devices = []
    for line in out.splitlines():
        m = DEVICE_LINE.match(line.strip())
        if m:
            devices.append({"mac": m.group(1), "name": m.group(2)})
    return devices

def get_info(mac):
    rc, out, _ = run_bctl([f"info {mac}"])
    info = {"paired": False, "trusted": False, "connected": False, "alias": None, "uuids": []}
    alias = None; uuids = []
    for line in out.splitlines():
        s = line.strip()
        b = BOOL_LINE.match(s)
        if b:
            key, val = b.group(1).lower(), (b.group(2).lower() == "yes")
            info[key] = val
        elif s.startswith("Alias:"):
            alias = s.split("Alias:", 1)[1].strip()
        elif s.startswith("UUID:"):
            uuids.append(s.split("UUID:", 1)[1].strip())
    info["alias"] = alias
    info["uuids"] = uuids
    return info

def is_audio_capable(info, name_hint=""):
    uuids = " ".join(info.get("uuids", [])).lower()
    if any(u in uuids for u in AUDIO_UUID_HINTS):
        return True
    name = (name_hint or "").lower()
    return any(k in name for k in AUDIO_NAME_HINTS)

def wait_info(mac, key, want=True, tries=12, delay=0.5):
    for _ in range(tries):
        info = get_info(mac)
        if bool(info.get(key)) == bool(want):
            return info
        time.sleep(delay)
    return get_info(mac)

# ------------------ Persistent scanner session ------------------
def _start_persistent_scan():
    if SCAN_PROC["p"] and SCAN_PROC["p"].poll() is None:
        return
    adapter = _get_adapter_mac()
    p = subprocess.Popen(
        ["bluetoothctl"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )
    SCAN_PROC["p"] = p
    SCAN_PROC["adapter"] = adapter
    init = []
    if adapter: init.append(f"select {adapter}")
    init += ["power on", "agent NoInputNoOutput", "default-agent", "pairable on", "scan on"]
    for c in init:
        try:
            p.stdin.write(c + "\n"); p.stdin.flush()
        except Exception:
            break

def _persistent_write(lines):
    p = SCAN_PROC.get("p")
    if not p or p.poll() is not None:
        _start_persistent_scan()
        p = SCAN_PROC["p"]
        time.sleep(0.4)
    for cmd in lines:
        try:
            p.stdin.write(cmd + "\n")
            p.stdin.flush()
        except Exception:
            pass

def _stop_persistent_scan():
    p = SCAN_PROC.get("p")
    SCAN_PROC["p"] = None; SCAN_PROC["adapter"] = None
    if not p: return
    try:
        if p.poll() is None:
            for c in ["scan off", "quit"]:
                try: p.stdin.write(c + "\n"); p.stdin.flush()
                except Exception: pass
            for _ in range(10):
                if p.poll() is not None: break
                time.sleep(0.1)
        if p.poll() is None:
            p.kill()
    except Exception:
        try: p.kill()
        except Exception: pass

@atexit.register
def _cleanup():
    _stop_persistent_scan()

# ------------------ Connect while holding the session ------------------
def bctl_connect_wait(mac, wait_s=8):
    """Send connect and keep the bluetoothctl session alive while polling."""
    adapter = _get_adapter_mac()
    p = subprocess.Popen(
        ["bluetoothctl"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    cmds = []
    if adapter: cmds.append(f"select {adapter}")
    cmds += ["power on", f"connect {mac}"]
    for c in cmds:
        try:
            p.stdin.write(c + "\n"); p.stdin.flush()
        except Exception:
            break

    t0 = time.time()
    last_out = []
    connected = False
    while time.time() - t0 < wait_s:
        try:
            line = p.stdout.readline()
            if not line:
                time.sleep(0.1)
            else:
                last_out.append(line)
                if "Connection successful" in line or "Connected: yes" in line:
                    connected = True
                    break
        except Exception:
            time.sleep(0.1)

        info = get_info(mac)
        if info.get("connected"):
            connected = True
            break

    try:
        p.stdin.write("quit\n"); p.stdin.flush()
    except Exception:
        pass
    try:
        p.terminate()
    except Exception:
        pass

    return connected, "".join(last_out)

# ------------------ API ------------------
@app.post("/api/scan_on")
def api_scan_on():
    SCAN_STATE["wanted"] = True
    try:
        _start_persistent_scan()
    except Exception:
        SCAN_STATE["wanted"] = False
        return jsonify({"ok": False, "status": {}, "log": ""})
    time.sleep(0.5)
    return jsonify({"ok": True, "status": adapter_status(), "log": ""})

@app.post("/api/scan_off")
def api_scan_off():
    SCAN_STATE["wanted"] = False
    _stop_persistent_scan()
    time.sleep(0.3)
    return jsonify({"ok": True, "status": adapter_status(), "log": ""})

@app.get("/api/scan_status")
def api_scan_status():
    st = adapter_status()
    running = SCAN_PROC["p"] is not None and SCAN_PROC["p"].poll() is None
    return jsonify({"status": st, "running": running, "wanted": SCAN_STATE["wanted"]})

@app.get("/api/devices")
def api_devices():
    audio_only = request.args.get("audio_only") in ("1","true","yes","on")
    base = list_devices()
    enriched = []
    for d in base:
        info = get_info(d["mac"])
        name = info.get("alias") or d.get("name") or ""
        d |= {"alias": info.get("alias")}
        d |= info
        if (not audio_only) or is_audio_capable(info, name) or info.get("paired") or info.get("connected"):
            enriched.append(d)
    enriched.sort(key=lambda x: (not x.get("connected"), not x.get("paired"), (x.get("alias") or x.get("name") or "")))
    return jsonify({"devices": enriched})

@app.get("/api/info")
def api_info():
    mac = request.args.get("mac","")
    return jsonify(get_info(mac))

@app.post("/api/connect")
def api_connect():
    mac = request.json.get("mac","")
    logs = []

    def logstep(tag, out=""):
        logs.append(f"\x1b[1m== {tag}\x1b[0m\n{out}")

    # Pair (while scanning) to avoid "Device not available"
    _start_persistent_scan()
    logstep("scan-on")
    _persistent_write(["pairable on", f"pair {mac}"])
    time.sleep(1.0)
    info = wait_info(mac, "paired", True, tries=12, delay=0.5)
    if not info.get("paired"):
        raw = clean_for_js("\n".join(logs))
        return jsonify({"ok": False, "stage": "pair", "info": info, "log": raw}), 500
    logstep("pair-ok")

    # Stop scanning
    _stop_persistent_scan()
    logstep("scan-off")

    # Trust only if needed
    info = get_info(mac)
    if not info.get("trusted"):
        rc, out, err = run_bctl([f"trust {mac}"])
        logstep("trust", out + err)
        info = wait_info(mac, "trusted", True, tries=6, delay=0.4)
    else:
        logstep("trust-skip", "device is already trusted")

    # Connect (hold session open like interactive bluetoothctl)
    connected = False
    for attempt in range(1, 3):  # up to 2 tries
        ok, live_out = bctl_connect_wait(mac, wait_s=8)
        logstep(f"connect (held session, try {attempt})", live_out)
        info = wait_info(mac, "connected", True, tries=8, delay=0.5)
        if ok or info.get("connected"):
            connected = True
            break
        # nudge before retry
        rc2, out2, err2 = run_bctl([f"disconnect {mac}"])
        logstep(f"disconnect-before-retry {attempt}", out2 + err2)
        time.sleep(0.8)

    raw = clean_for_js("\n".join(logs))
    return jsonify({"ok": connected, "info": info, "log": raw})

@app.post("/api/disconnect")
def api_disconnect():
    mac = request.json.get("mac","")
    rc, out, err = run_bctl([f"disconnect {mac}"])
    info = wait_info(mac, "connected", False, tries=6, delay=0.4)
    txt = f"\x1b[1m== disconnect\x1b[0m\n{out}{err}"
    return jsonify({"ok": not info.get("connected", False), "info": info, "log": clean_for_js(txt)})

@app.post("/api/forget")
def api_forget():
    mac = request.json.get("mac","")
    info = get_info(mac)
    if info.get("connected"):
        run_bctl([f"disconnect {mac}"]); time.sleep(0.2)
    rc, out, err = run_bctl([f"remove {mac}"])
    txt = f"\x1b[1m== remove\x1b[0m\n{out}{err}"
    # Best-effort result; devices list will reflect reality
    return jsonify({"ok": True, "log": clean_for_js(txt)})

@app.post("/github-webhook")
def github_webhook():
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not signature.startswith("sha256="):
            return jsonify({"ok": False, "error": "invalid signature"}), 400
        sig = signature.split("=", 1)[1]
        mac = hmac.new(secret.encode(), request.data, hashlib.sha256)
        if not hmac.compare_digest(mac.hexdigest(), sig):
            return jsonify({"ok": False, "error": "bad signature"}), 403
    if request.headers.get("X-GitHub-Event") == "push":
        script = os.environ.get("GITHUB_WEBHOOK_SCRIPT", DEFAULT_WEBHOOK_SCRIPT)
        try:
            subprocess.Popen(["bash", script])
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True})

@app.get("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
