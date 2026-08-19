# Part 1 Roadmap — Ingest Jobs Without Getting Burned

Self-serve plan for the Acdyon **Part 1 (scraper)** track. Demo one legal source end-to-end; use the design doc to show how the same pattern would survive a hostile board.

> **Scope guardrail:** Run the live demo against a public job RSS/API or a sandbox you control — **not** a live LinkedIn, Indeed, Naukri, or Wellfound account. They want the ingestion pattern, not a banned IP.

---

## At a glance

| | Weekend learn | Challenge sprint |
|---|---|---|
| **Total time** | ~10h 10m | ~6h 40m |
| **Best for** | Learning the pieces as you go | You already know your stack |
| **Slack to add** | ~20% for deploy surprises | ~20% for deploy surprises |

**Submit artifacts:** live deployed URL · GitHub repo · `DECISIONS.md` (1 page)

---

## Time budget by kind of work (weekend pace)

| Category | Time | Steps |
|---|---|---|
| Research & framing | 2h | 0, 1 |
| Build pipeline | 5h | 2, 3, 4, 5 |
| Docs | 1h 15m | 6 |
| Ship & rehearse | 1h 45m | 7, 8 |

---

## Quick reference

| Step | Weekend | Sprint | Done when |
|---|---|---|---|
| 0. Frame the problem | 45 min | 20 min | One-sentence pitch + named source, fallback, and three artifacts |
| 1. Detection surface | 75 min | 40 min | 5+ signals listed; each marked accounted-for, out-of-scope, or refused |
| 2. Legal source + schema | 45 min | 25 min | Primary URL works; fixture JSON in repo; schema written down |
| 3. Happy-path ingest | 90 min | 70 min | Ingest + query real jobs locally; bad records logged, not stored |
| 4. Resilience | 100 min | 70 min | Dead primary still shows jobs + degraded badge; invalid payload = failed run |
| 5. Demo screen | 75 min | 50 min | localhost shows ingested jobs and pipeline health |
| 6. Design doc + DECISIONS.md | 75 min | 50 min | Docs are gradable without a call; DECISIONS.md names a rejected alternative |
| 7. Deploy + submit | 60 min | 45 min | Live URL works without your laptop; repo matches production |
| 8. Own every line | 45 min | 30 min | You can draw the pipeline from memory; no "the model suggested it" |

---

## Step-by-step guide

### 0. Frame the problem, not the scraper

**Weekend:** 45 min · **Sprint:** 20 min

**Why:** The brief is grading a pipeline that survives detection and failure — not a LinkedIn bypass. If you start in Playwright, you will optimize the wrong thing.

**How to do it alone:**

1. Re-read Part 1, the scope guardrail, and the grading table. Circle one sentence: *"how you get it out at all, repeatedly, without getting burned."*
2. Write a 10-line personal brief: source you will actually hit, schema you will store, what the live demo shows, and what you will refuse to scrape.
3. Pick a stack you can explain line-by-line. Fastest honest choice is usually Python + FastAPI or Node + Hono/Express, plus SQLite.
4. Create an empty GitHub repo now so deploy is not a last-hour surprise.

**Expected after this step:**

- [ ] You can say in one sentence what you will ship.
- [ ] You have named a low-risk primary source and a fallback.
- [ ] You know the three submission artifacts: live URL, repo, `DECISIONS.md`.

**Usual failure:** Treating this as "scrape LinkedIn." That violates the guardrail, their ToS, and is not what they asked you to demo.

---

### 1. Map the detection surface (study, don't attack)

**Weekend:** 75 min · **Sprint:** 40 min

**Why:** Section 1 of the design doc is the systems-thinking test. You need specific signals, not "they block bots."

**How to do it alone:**

1. Make a table with columns: signal, why a site uses it, does my demo hit it, how a production design would account for it.
2. Cover at least: inconsistent or missing headers, datacenter IP reputation, perfectly regular timing, no cookie/session continuity, headless-browser tells, TLS/JA3 fingerprint mismatch.
3. Read public overviews of bot management (Cloudflare docs on bot fight / fingerprinting primers). Stop at understanding — you are not building a stealth browser.
4. Be honest: a public JSON/RSS source barely triggers this surface. Say so, then describe how the same pipeline would change if the source were a hostile HTML board.

**Expected after this step:**

- [ ] Detection-surface draft lists 5+ concrete signals.
- [ ] Each signal is marked accounted-for, out-of-scope-for-demo, or refused-on-principle.

**Usual failure:** Writing "use undetected Chrome and rotate proxies" with no mechanism, no failure mode, and no line you will not cross.

---

### 2. Pick a legal source and freeze a job schema

**Weekend:** 45 min · **Sprint:** 25 min

**Why:** The live demo must run against one low-risk source. Everything else is design, not the URL they click.

**How to do it alone:**

1. Pick one public feed you can open in a browser with no login: Arbeitnow job-board API, RemoteOK JSON, USAJobs, or a job-board RSS. Verify its terms yourself.
2. Commit a fixture file of 8–15 normalized jobs. This is plan B when the network or the source dies during their review.
3. Freeze a schema: `id`, `title`, `company`, `location`, `url`, `source`, `fetchedAt`. Validate every record against it.
4. Write the "where you'd stop" paragraph now, while you still mean it: no logged-in accounts, no CAPTCHA farms, no ToS-breaking targets in the demo.

**Expected after this step:**

- [ ] Primary URL returns data in your browser.
- [ ] Fixture JSON exists in the repo.
- [ ] Schema is written down, not improvised in parse code.

**Usual failure:** Choosing a source that needs cookies or an account. That turns a design challenge into an account-ban story.

---

### 3. Build the happy-path ingest loop

**Weekend:** 90 min · **Sprint:** 70 min

**Why:** You cannot talk about resilience until a single clean fetch-parse-store-serve path exists.

**How to do it alone:**

1. One module: fetch with an explicit timeout, parse JSON/XML, validate, upsert into SQLite (or a JSON file if you must).
2. Expose two endpoints: `POST`/`GET /ingest` (or a CLI) and `GET /jobs`.
3. Log source, latency, item count, and outcome on every run. You will reuse this in the demo UI.
4. Keep identity boring: a real User-Agent, Accept headers, and a minimum interval between requests — even on a public API. That is the ingestion-strategy sketch, not stealth.

**Expected after this step:**

- [ ] From your machine you can ingest and then query a list of real jobs.
- [ ] Invalid records are dropped with a log line, not silently stored.

**Usual failure:** A notebook that prints jobs once. If it is not a repeatable pipeline, it is not the deliverable.

---

### 4. Add resilience — this is the grade

**Weekend:** 100 min · **Sprint:** 70 min

**Why:** They ask what happens when markup changes, you are rate-limited, or the body is empty. Silent empty is a fail.

**How to do it alone:**

1. **Retries:** 2–3 attempts, exponential backoff with jitter. Never a tight retry loop.
2. **Circuit breaker:** after N consecutive failures, stop hitting the primary, serve last-good cache, mark source degraded.
3. **Fallback:** switch to the second feed or the committed fixture. The UI must show which source served the page.
4. **Fail loud:** empty body, HTTP 429, or schema mismatch is an error state, not zero jobs.
5. **Optional but strong:** a tiny "parser version" or checksum so a shape change is visible in logs.

**Expected after this step:**

- [ ] You can point the primary URL at a dead host and still see jobs plus a degraded/fallback badge.
- [ ] You can force an empty/invalid payload and the run is marked failed, not successful-with-zero.

**Usual failure:** Retrying forever, or swapping in fake jobs with no status. Honesty is a grading axis.

---

### 5. Ship a boring, truthful demo screen

**Weekend:** 75 min · **Sprint:** 50 min

**Why:** Part 1 is not graded on taste. They need to see listings come out of a living pipeline.

**How to do it alone:**

1. One page: job table, last run time, item count, source name, health (healthy / degraded / down).
2. A button or cron-style note for "run ingest" so a reviewer can watch a fetch happen.
3. Server-rendered HTML is enough. Do not start a design system.
4. Use the real titles and companies from the source. No invented counts.

**Expected after this step:**

- [ ] localhost shows jobs you ingested, not a hardcoded mock-only page.
- [ ] Pipeline health is visible without reading logs.

**Usual failure:** Spending the evening on CSS while the breaker and fallback are still comments.

---

### 6. Write the design doc and DECISIONS.md

**Weekend:** 75 min · **Sprint:** 50 min

**Why:** Half the deliverable is the document. The demo proves the pattern; the doc proves you thought past Tuesday.

**How to do it alone:**

1. One diagram: fetch → validate → store → serve, with a fallback branch and a circuit-open path.
2. **Section 1 — Detection surface:** your table from step 1, cleaned up.
3. **Section 2 — Ingestion strategy:** pacing, identity, rotation-as-design (not as a live proxy farm), and plan B when the source dies in a week.
4. **Section 3 — Resilience:** retries, breaker, fallback, loud failure. Point at code paths.
5. **Section 4 — Where you'd stop:** ToS, no authenticated scrape, no CAPTCHA solving, demo stays on the public feed.
6. **`DECISIONS.md`, one page:** why this strategy over headless-against-LinkedIn; one time-limit trade-off; where AI was used and what you changed.

**Expected after this step:**

- [ ] Someone can grade you from the docs without you on a call.
- [ ] `DECISIONS.md` is one page and names a rejected alternative.

**Usual failure:** Generic AI prose that could apply to any scraper. They will ask you to defend every paragraph.

---

### 7. Deploy, README, submit

**Weekend:** 60 min · **Sprint:** 45 min

**Why:** Ungraded locally is unsubmitted. Free hosts flake; leave slack.

**How to do it alone:**

1. README: what it is, which source, how to run locally, how to trigger ingest, how fallback is demonstrated.
2. Deploy to Railway, Render, or Fly. Put the source URL and any keys in env vars.
3. Click the live URL in an incognito window and on your phone.
4. Submit the form once: deployed URL, GitHub link. One entry.

**Expected after this step:**

- [ ] Live URL loads without your laptop.
- [ ] Repo is public and matches what is deployed.

**Usual failure:** First deploy at submit time. Cold starts, missing env, and SQLite-on-ephemeral-disk are the usual failures.

---

### 8. Rehearse until you own every line

**Weekend:** 45 min · **Sprint:** 30 min

**Why:** Ownership is a grading axis. AI is allowed; unexplained AI is not.

**How to do it alone:**

1. Walk every file out loud. If you cannot explain a retry constant, delete or rewrite it.
2. Practice: why not Playwright on LinkedIn; what happens if markup changes overnight; what is plan B in a week; where you personally stop.
3. Keep a cheat sheet of three decisions you will defend first.

**Expected after this step:**

- [ ] No answer sounds like "the model suggested it."
- [ ] You can draw the pipeline from memory.

**Usual failure:** Leaving generated comments and unused stealth libraries in the repo. Reviewers read the tree.

---

## What to ship

### Live demo
Deployed URL that pulls listings from one legal source, stores them, and shows health. Fallback must be demonstrable.

### GitHub repo
Runnable locally, README, no secrets. Code should match the design doc — reviewers will cross-check.

### DECISIONS.md
One page: why this strategy, one time-limit trade-off, where AI was used and what you verified.

---

## Recommended architecture (keep it small)

```
Primary fetch (public API or RSS)
  → validate against schema
  → upsert SQLite
  → serve /jobs + status page

On 429, timeout, empty body, or schema miss:
  → backoff
  → circuit-open
  → fixture fallback
```

- **Identity:** stable User-Agent + pacing
- **Rotation / multi-IP:** described in the doc, not required in the demo

**Suggested primary sources:** Arbeitnow public job API, RemoteOK JSON, or USAJobs.

**Suggested fallback:** committed fixture JSON in the repo.

Confirm terms before you hit anything.

---

## How they grade Part 1

| Axis | What to prove |
|---|---|
| **Systems thinking** | Mid-run block, empty body, or shape change does not silently zero out the UI. Fallback and status are visible. |
| **Honesty** | Real listings from a real allowed source. No fake counts. Docs admit what the demo does not do. |
| **Ownership** | You can defend pacing, breaker thresholds, source choice, and the ToS line without citing the model. |
| **UI craft** | Not the Part 1 axis. Make the demo readable; spend the minutes on the pipeline. |

---

## Two-day calendar (weekend pace)

### Day 1 — pattern works locally

- **Morning:** steps 0–2 (2h 45m)
- **Afternoon:** steps 3–4 (3h 10m)
- **Stop when:** fallback is demoable on localhost

### Day 2 — prove it remotely

- **Morning:** demo UI + docs (2h 30m)
- **Afternoon:** deploy, README, form, rehearsal (1h 45m)
- **Leave the last hour** for a cold-start failure

---

## Checklist

- [ ] 0. Frame the problem, not the scraper · 45 min
- [ ] 1. Map the detection surface · 75 min
- [ ] 2. Pick a legal source and freeze a job schema · 45 min
- [ ] 3. Build the happy-path ingest loop · 90 min
- [ ] 4. Add resilience — this is the grade · 100 min
- [ ] 5. Ship a boring, truthful demo screen · 75 min
- [ ] 6. Write the design doc and DECISIONS.md · 75 min
- [ ] 7. Deploy, README, submit · 60 min
- [ ] 8. Rehearse until you own every line · 45 min

---

Submit through the [assessment form](https://forms.gle/qeqpHhvYGWA3ftY69) with deployed URL + repo. **One track only** — do not also start the home page.
