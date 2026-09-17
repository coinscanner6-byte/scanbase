#!/bin/bash
# Sets up this new Scanbase folder on your Mac.
# It only COPIES your .env from the old folder - the old folder is untouched.
#
# Usage (from inside this folder):
#   bash setup_mac.sh ~/Downloads/scanbase_apikeys
#
# Safe: it does NOT change the live database. That's a separate step.

set -e

OLD="$1"
if [ -z "$OLD" ]; then
  echo "Tell me where the OLD folder is, e.g.:"
  echo "  bash setup_mac.sh ~/Downloads/scanbase_apikeys"
  exit 1
fi

if [ ! -f "$OLD/.env" ]; then
  echo "No .env found in $OLD"
  echo "Find it with:  find ~/Downloads -name .env -path '*scanbase*'"
  exit 1
fi

if [ -f ".env" ]; then
  echo ".env already here - keeping it."
else
  cp "$OLD/.env" .env
  echo "Copied .env from $OLD"
fi

echo "Creating a private Python environment (venv)..."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt -r requirements-dev.txt

echo ""
echo "Running offline tests..."
python3 -m pytest -q

echo ""
echo "Checking database size (read-only)..."
python3 -m scripts.db_size

echo ""
echo "============================================================"
echo "SETUP DONE. Nothing on the live database was changed."
echo "Paste everything above to Claude before the next step."
echo "============================================================"
