"""
# Architecture

The live demo is a **resilient ingestion pipeline**, not a platform bypass.

![Architecture](diagrams/architecture.png)

```
Public source
    → Firecrawl (primary) or polite HTTP GET for public JSON/RSS
        → content/transport validation
            → Selenium fallback if empty / 429 / anomaly
    → Raw crawl stored in process memory
    → Clean + fingerprint / dedup
    → Gemini structured extraction
    → Schema + business validation
    → Job objects stored in runtime memory
    → Streamlit UI (print as-is + ✕ delete) and optional Flask API
```

## Layers

| Layer | Module | Role |
|---|---|---|
| Config | `app/config` | Env-based settings and logging |
| Clients | `app/clients` | Firecrawl SDK, Selenium, Gemini SDK |
| Crawlers | `app/crawlers` | Adapters that return `FetchResult` |
| Extractors | `app/extractors` | Gemini unstructured → JSON objects |
| Processors | `app/processors` | Clean, canonicalize, dedup, normalize |
| Validators | `app/validators` | Crawl health + job schema |
| Repositories | `app/repositories` | **In-memory** dicts (demo persistence) |
| Services | `app/services` | Orchestration + metrics |
| API | `app/api` | Flask JSON |
| UI | `streamlit_app.py` | Operator dashboard |

## Persistence choice

The design document mentions PostgreSQL for a production system. The demo
store is **process memory** so Streamlit can show Gemini objects immediately
and delete them with ✕ without running a database.

Raw crawls are also kept in memory (`CrawlRepository`) so extraction can be
re-run without fetching again.

## Failure handling

- HTTP 429 → back off; never increase request volume
- Empty / tiny / marker-less body → anomaly, try Selenium, then mark degraded
- Invalid Gemini objects → rejected, counted, not stored
- Repeated failures → circuit opens; operator must wait / reset

## Boundary

The system uses public URLs, official APIs, and RSS. It does **not** solve
CAPTCHAs, log into accounts, or rotate identity to evade blocks.
"""
