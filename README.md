# Bluetooth Control Web UI (Raspberry Pi Zero 2 W · Debian 12)

A small Flask + Bootstrap web app to scan, pair, trust, connect, disconnect, and forget Bluetooth devices — optimized for **audio** (A2DP/AVRCP via BlueZ + BlueALSA).
Open it from any browser on your LAN.

---

## Tested setup

- Hardware: **Raspberry Pi Zero 2 W**
- OS: **Debian GNU/Linux 12 (Bookworm) – aarch64**
- Kernel: **6.12.41-v8+**
- Bluetooth: **BlueZ 5.x**
- Audio: **bluez-alsa-utils** (modern replacement for `bluealsa`)

---

## 1) System prep (no pip/venv)

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Install required packages (note: **bluez-alsa-utils** is the new package name):

```bash
sudo apt install -y   bluetooth bluez bluez-tools bluez-alsa-utils alsa-utils   python3-flask git
sudo rfkill unblock bluetooth
sudo systemctl enable --now bluetooth
```

---

## 2) Get the app into place

> If you’re using this as a GitHub repo, replace `<your-username>/<your-repo>` below.

```bash
sudo mkdir -p /opt/bt-web
cd /opt
sudo git clone https://github.com/<your-username>/<your-repo>.git bt-web
sudo chown -R pi:pi /opt/bt-web
```

Your tree should look like:

```
/opt/bt-web
├── app.py
├── templates/
│   └── index.html
└── static/
    ├── script.js
    └── style.css
```

---

## 3) Quick test (foreground)

```bash
python3 /opt/bt-web/app.py
```

Then in a browser on your network:

```
http://<Host IP>:8080/
```

Press **Scan On**, put your speaker in pairing mode, select it, then **Connect**.

Stop the app with `Ctrl+C` when done testing.

---

## 4) Run as a service (systemd)

Create the service file:

```bash
sudo tee /etc/systemd/system/bt-web.service > /dev/null << 'EOF'
[Unit]
Description=Bluetooth Web UI
After=bluetooth.service network-online.target
Wants=bluetooth.service network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/bt-web
ExecStart=/usr/bin/python3 /opt/bt-web/app.py
Environment=PORT=8080
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bt-web
sudo systemctl status bt-web --no-pager
```

Open the app at:

```
http://<Host IP>:8080/
```

---

## 5) (Optional) Audio test with BlueALSA

Once **Connected** to your speaker, play the test sound:

```bash
# Find the bluealsa device strings
aplay -L | grep -A2 bluealsa

# Use your speaker's MAC in DEV=
aplay -D bluealsa:DEV=<Speaker-MAC>,PROFILE=a2dp /usr/share/sounds/alsa/Front_Center.wav
```

---

## 6) Auto-update via GitHub webhook

The app can listen for GitHub webhooks and trigger a local script on each push.

1. Create a webhook in your GitHub repository pointing to:

   `http://<Host IP>:8080/github-webhook`

2. Set a **secret** for the webhook and export it before starting the app:

   ```bash
   export GITHUB_WEBHOOK_SECRET="<your-secret>"
   ```

3. (Optional) Specify a script to run (defaults to `deploy.sh` in the project root):

   ```bash
   export GITHUB_WEBHOOK_SCRIPT="/path/to/your/script.sh"
   ```

On each push, the script executes in the background, allowing simple auto-deployments.

---

## How it works (summary)

- **Scan On** starts a persistent `bluetoothctl` session that keeps scanning.
- **Connect** workflow:
  1) Pair in the active scan session (fixes “Device not available”)
  2) Stop scanning
  3) Trust the device (skipped if already trusted)
  4) **Connect while holding a live `bluetoothctl` session** until the link is confirmed
- The UI uses **Bootstrap** and renders logs client-side with **ansi-to-html**.
- “Audio only” filter shows likely audio devices (A2DP/AVRCP UUIDs or common brand hints).

---

## Troubleshooting

**Nothing shows up when scanning**
- Put the speaker in pairing mode (hold the Bluetooth button until it announces pairing).
- Make sure it’s **not** already connected to your phone (toggle BT off on the phone for a minute).
- Restart BlueZ:
  ```bash
  sudo systemctl restart bluetooth
  ```

**Pair works but Connect doesn’t**
- Try the same command by SSH:
  ```bash
  bluetoothctl connect <MAC>
  ```
  If that works instantly but the web app doesn’t, ensure you’re on the latest app (we keep the session open while connecting).

**Check logs**
```bash
journalctl -u bluetooth --since "10 min ago" --no-pager
systemctl status bt-web --no-pager
```

**Reset adapter (rare)**
```bash
sudo systemctl stop bluetooth
sudo hciconfig hci0 down
sudo hciconfig hci0 up
sudo systemctl start bluetooth
```

---

## Security / Network

- The app binds to `0.0.0.0:8080` (LAN-only typical).  
  If you expose it beyond your LAN, put it behind a reverse proxy with auth.

---

## License

TBD