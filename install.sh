#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a fresh Raspberry Pi (Debian 12) with the Bluetooth Web UI
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Muppet1856/BluetoothWebsite/main/install.sh | sudo bash
# or
#   REPO_URL=https://github.com/Muppet1856/BluetoothWebsite.git bash install.sh

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Error: run this script as root" >&2
  exit 1
fi

REPO_URL=${REPO_URL:-https://github.com/Muppet1856/BluetoothWebsite.git}
DEST=/opt/bt-web
SERVICE=/etc/systemd/system/bt-web.service

apt update
apt full-upgrade -y
apt install -y bluetooth bluez bluez-tools bluez-alsa-utils alsa-utils python3-flask git

rfkill unblock bluetooth
systemctl enable --now bluetooth

if [[ ! -d "$DEST" ]]; then
  git clone "$REPO_URL" "$DEST"
else
  git -C "$DEST" pull --ff-only
fi

if ! id -u bt-web >/dev/null 2>&1; then
  adduser --system --group bt-web
fi
chown -R bt-web:bt-web "$DEST"

cp "$DEST/bt-web.service" "$SERVICE"
systemctl daemon-reload
systemctl enable --now bt-web

echo "\nDeployment complete. Service status:"
systemctl status bt-web --no-pager
