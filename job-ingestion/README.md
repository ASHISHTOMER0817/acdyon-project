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

## Deploy on Railway

Use **two services** in one Railway project if you want both Streamlit and Flask. Each gets its own free `*.up.railway.app` domain. They do **not** share in-memory job data.

### Service 1 — Streamlit UI

1. Push this repo to GitHub (`ASHISHTOMER0817/acdyon-project`).
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
3. Leave **Root Directory** empty (repo root). Railway uses root `Dockerfile` + `railway.toml`.
4. Add **Variables**:

   | Variable | Required | Example |
   |---|---|---|
   | `GEMINI_API_KEY` | Yes | your Google AI key |
   | `FIRECRAWL_API_KEY` | No | Firecrawl key (optional) |
   | `DEFAULT_SOURCE_URL` | No | `https://remoteok.com/api` |
   | `DEFAULT_SOURCE_NAME` | No | `remoteok` |
   | `GEMINI_MODEL` | No | `gemini-3.6-flash` |

5. **Settings → Networking → Generate Domain** → set target port to **`8080`**.
6. Open the URL and click **Run ingest**.

Default start command (from Dockerfile): `sh start.sh`

### Service 2 — Flask API

1. In the **same Railway project**: **+ New** → **GitHub Repo** → select the same repo.
2. Leave **Root Directory** empty (same root `Dockerfile`).
3. **Settings → Deploy → Start Command**:
   ```bash
   sh flask_start.sh
   ```
4. **Settings → Deploy → Health Check Path**: `/health`
5. Add the same **Variables** as Streamlit (`GEMINI_API_KEY`, etc.). Do **not** set `PORT` manually.
6. **Settings → Networking → Generate Domain** → target port **`8080`**.
7. Test: `GET https://your-api.up.railway.app/health` and `GET https://your-api.up.railway.app/jobs`

Flask binds to `0.0.0.0` and reads Railway's `PORT` automatically (via `settings.py`).

**Notes for Railway:**
- Selenium fallback is **not** available in the container (no Chrome). Use public JSON/RSS URLs like RemoteOK.
- Job objects live in **process memory** — they reset if the service redeploys or sleeps.
- Do **not** commit `.env`; set secrets only in Railway Variables.

**If the URL returns 502 or won't load:**
1. Use your `https://….up.railway.app` domain — **not** the `External URL` IP from deploy logs.
2. **Settings → Networking → Public Networking**: ensure a domain exists and the **target port is `8080`** (must match the `PORT` line in deploy logs).
3. Do **not** set `PORT=8501` in Variables; Railway assigns `8080` automatically.
4. Streamlit health check: `/_stcore/health`. Flask health check: `/health`.
