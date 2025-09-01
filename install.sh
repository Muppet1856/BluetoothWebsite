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

# Prompt for optional GitHub webhook passphrase and hash it
WEBHOOK_SECRET_HASH=""
read -s -p "Enter GitHub webhook passphrase (leave blank to skip): " WEBHOOK_PASS
echo
if [[ -n "$WEBHOOK_PASS" ]]; then
  read -s -p "Confirm GitHub webhook passphrase: " WEBHOOK_PASS_CONFIRM
  echo
  if [[ "$WEBHOOK_PASS" != "$WEBHOOK_PASS_CONFIRM" ]]; then
    echo "Error: passphrases do not match" >&2
    exit 1
  fi
  WEBHOOK_SECRET_HASH=$(printf '%s' "$WEBHOOK_PASS" | sha256sum | cut -d' ' -f1)
  unset WEBHOOK_PASS WEBHOOK_PASS_CONFIRM
  echo "Hashed webhook secret: $WEBHOOK_SECRET_HASH"
fi

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
if [[ -n "$WEBHOOK_SECRET_HASH" ]]; then
  sed -i "s|# Environment=GITHUB_WEBHOOK_SECRET=your-hash|Environment=GITHUB_WEBHOOK_SECRET=$WEBHOOK_SECRET_HASH|" "$SERVICE"
fi
systemctl daemon-reload
systemctl enable --now bt-web

echo "\nDeployment complete. Service status:"
systemctl status bt-web --no-pager
