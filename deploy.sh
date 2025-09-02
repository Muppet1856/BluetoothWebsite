#!/usr/bin/env bash
set -euxo pipefail
echo "Running as $(whoami)"

# Always run from the location of this script
cd "$(dirname "$0")"

# Update repo
# Branch priority: 1) argument, 2) GitHub Actions vars, 3) default to main
BRANCH="${1:-${GITHUB_REF_NAME:-${GITHUB_HEAD_REF:-${GITHUB_REF#refs/heads/}}}}"
BRANCH="${BRANCH:-main}"
echo "Updating repository on branch $BRANCH..."
git fetch origin "$BRANCH"
git checkout "$BRANCH" || git checkout -b "$BRANCH" "origin/$BRANCH"
git pull --ff-only origin "$BRANCH"

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
