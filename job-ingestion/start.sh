#!/bin/sh
# Railway injects $PORT at runtime. Fall back to 8501 for local Docker runs.
set -e
PORT="${PORT:-8501}"

exec streamlit run streamlit_app.py \
  --server.port="$PORT" \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false
