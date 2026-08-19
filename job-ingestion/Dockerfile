FROM python:3.11-slim

WORKDIR /app

# Minimal OS deps. Selenium/Chrome is not installed — use public JSON/RSS on Railway.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x start.sh flask_start.sh

ENV PYTHONUNBUFFERED=1

# Railway sets $PORT; start.sh binds Streamlit to it.
CMD ["./start.sh"]
