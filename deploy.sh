#!/usr/bin/env bash
set -euxo pipefail
echo "Running as $(whoami)"

# Always run from the location of this script
cd "$(dirname "$0")"

# Update repo
echo "Updating repository..."
git pull --ff-only origin main

# Print the current version
echo "Deploying version $(cat VERSION)"

# Copy repo to deployment directory
DEST="/opt/bt-web"
echo "Syncing files to $DEST..."
mkdir -p "$DEST"
rsync -a --delete . "$DEST/"

# Restart service
echo "Restarting bt-web service..."
if ! sudo -n true; then
  echo "Error: sudo privileges are required to restart bt-web" >&2
  exit 1
fi
sudo systemctl daemon-reload
sudo systemctl restart bt-web
sudo systemctl status bt-web --no-pager
