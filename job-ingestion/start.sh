#!/bin/sh
# Railway injects $PORT and RAILWAY_PUBLIC_DOMAIN at runtime.
set -e
PORT="${PORT:-8501}"

echo "=== Railway startup ==="
echo "PORT=${PORT}"
echo "RAILWAY_PUBLIC_DOMAIN=${RAILWAY_PUBLIC_DOMAIN:-not set}"
echo "Set Public Networking target port to ${PORT} in Railway if the URL returns 502."
echo "======================="

set -- streamlit run streamlit_app.py \
  --server.port="$PORT" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --server.fileWatcherType=none \
  --browser.gatherUsageStats=false

if [ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]; then
  set -- "$@" \
    --browser.serverAddress="$RAILWAY_PUBLIC_DOMAIN" \
    --browser.serverPort=443
fi

exec "$@"
