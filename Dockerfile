FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY job-ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY job-ingestion/ .
RUN chmod +x start.sh

ENV PYTHONUNBUFFERED=1

# Use sh so the script runs even if shebang/execute bits differ; env vars still apply.
CMD ["sh", "start.sh"]
