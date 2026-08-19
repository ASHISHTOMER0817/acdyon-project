# Job listing ingestion

Resilient pipeline for **public** job sources:

**Fetch → (Selenium fallback) → store raw crawl → clean/dedup → Gemini objects → validate → in-memory store → Streamlit / Flask**

This is the Acdyon Part 1 demo: the ingestion *pattern*, not a LinkedIn bypass.

## What you get

- **Streamlit UI** — run ingest, print each Gemini object as-is, **✕** deletes it from memory
- **Optional Flask API** — `POST /jobs/ingest`, `GET /jobs`, `DELETE /jobs/<id>`, `GET /health`
- Firecrawl primary fetch, Selenium fallback, Gemini extraction
- Runtime **local memory** (process dict), not PostgreSQL — objects appear as soon as Gemini returns them

## Quick start (Windows)

```powershell
cd "C:\Users\ashis\Desktop\acdyon project\job-ingestion"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env and set GEMINI_API_KEY
streamlit run streamlit_app.py
```

Open http://localhost:8501

Paste a **public** job API/RSS URL (default is RemoteOK’s public JSON API), click **Run ingest**. After Gemini returns objects they are stored in memory and rendered as JSON. Click **✕** on any card to delete that object.

### Optional Flask API

```powershell
python -m app.api.app
```

http://127.0.0.1:8000/jobs

Streamlit and Flask are **separate processes** with separate memory. Use Streamlit for the demo UI.

### Tests

```powershell
pytest -q
```

### One-shot CLI ingest

```powershell
python scripts\run_ingestion.py --url https://remoteok.com/api
```

## Environment

See `.env.example`.

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | **Yes** for live extract | Turns crawled text into job objects |
| `FIRECRAWL_API_KEY` | No | Primary HTML scrape; without it, public JSON/RSS uses HTTP GET |
| `DEFAULT_SOURCE_URL` | No | Demo source (default RemoteOK API) |

## Project layout

Matches the agreed package layout under `app/` (config, models, schemas, clients, crawlers, extractors, processors, validators, repositories, services, workers, api). Docs live in `docs/`. Tests mirror those layers.

## Design notes

- Detection surface, fallback, and “where we stop” are documented in `docs/architecture.md` and `docs/ingestion-strategy.md`.
- Original design: `docs/job_listing_ingestion_design.md`.
- Gemini is **extraction**, not validation. Invalid objects are rejected.
- HTTP 429 → back off. The client never ramps up after a rate limit.
- CAPTCHA / login walls → stop. No solving, no account reuse.

## Docker

```powershell
docker compose up streamlit
```

Flask profile: `docker compose --profile api up flask`
