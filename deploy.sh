#!/usr/bin/env bash
set -e

# Always run from the location of this script
cd "$(dirname "$0")"

# Update repo
git pull --ff-only

# Print the current version
echo "Deploying version $(cat VERSION)"

# Copy repo to deployment directory
DEST="/opt/bt-web"
mkdir -p "$DEST"
rsync -a --delete . "$DEST/"

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart bt-web
