#!/bin/sh
# Flask API entrypoint for a second Railway service (same Docker image as Streamlit).
set -e
PORT="${PORT:-8000}"

echo "=== Railway Flask startup ==="
echo "PORT=${PORT}"
echo "RAILWAY_PUBLIC_DOMAIN=${RAILWAY_PUBLIC_DOMAIN:-not set}"
echo "Set Public Networking target port to ${PORT} in Railway if the URL returns 502."
echo "Health check path: /health"
echo "============================="

exec python -m app.api.app
