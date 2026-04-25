#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "==> Building worker with inlined HTML..."
python3 build.py

echo "==> Deploying worker..."
wrangler deploy

echo "==> Done!"
