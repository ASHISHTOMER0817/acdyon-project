#!/bin/sh
# Railway injects $PORT and RAILWAY_PUBLIC_DOMAIN at runtime.
set -e
PORT="${PORT:-8501}"

# Base args for container / reverse-proxy hosting.
set -- streamlit run streamlit_app.py \
  --server.port="$PORT" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --browser.gatherUsageStats=false

# Without this, Streamlit websocket URLs point at localhost and the page never loads.
if [ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]; then
  set -- "$@" \
    --browser.serverAddress="$RAILWAY_PUBLIC_DOMAIN" \
    --browser.serverPort=443
fi

exec "$@"
