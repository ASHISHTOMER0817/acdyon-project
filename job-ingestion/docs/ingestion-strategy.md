"""
# Ingestion strategy

## Primary path

1. **Firecrawl** scrapes the URL to HTML + Markdown when `FIRECRAWL_API_KEY` is set.
2. If Firecrawl is unset or fails, a **single polite HTTP GET** is used. This
   is how the default RemoteOK JSON API demo works without a Firecrawl key.
3. Requests are paced (`MIN_REQUEST_INTERVAL_SECONDS`) and retried with
   exponential backoff, capped by `MAX_RETRIES`.

## Fallback path

Selenium (headless Chrome) runs only when the primary result is a transport
failure or a **content anomaly** (empty body, too small, no job markers, 429).

If Selenium hits a CAPTCHA or access challenge, it **stops**. That is
intentional.

## Extraction

Gemini converts crawled text into a JSON envelope `{ "jobs": [ ... ] }`.
Each object is validated (`title`, `company`, `source_url` required) before
it is written to `JobRepository`.

The Streamlit UI prints `gemini_object` as-is. The ✕ button deletes that
id from the in-memory dict.

## Dedup

`job_id = sha256(source + canonical_url)[:16]`

Tracking query params are stripped. If the URL is missing, a fingerprint of
`company + title + location` is used.

Dedup happens after Gemini returns objects and before insert. Duplicates are
counted in health metrics so a "zero new jobs" run is visible.

## Plan B if the source dies

1. Selenium fallback (if permitted and not a challenge page)
2. Cooldown + circuit open
3. Operator switches `DEFAULT_SOURCE_URL` to another public source
4. Adapter isolation: only the crawler for that source needs to change

Plan B is **source diversification**, not a more aggressive scraper.

## Demo source

Default: `https://remoteok.com/api` (public JSON). Confirm terms before use.
Do not point this demo at LinkedIn, Indeed, Naukri, or Wellfound accounts.
"""
