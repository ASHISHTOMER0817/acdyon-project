# Job Listing Ingestion System --- Design

## 1. Overview

The system is designed to ingest job listings from a permitted public
job source and transform heterogeneous crawled content into a
consistent, structured job-listing schema.

The ingestion architecture separates fetching, raw-data preservation,
extraction, validation, and storage. Firecrawl is the primary fetching
mechanism, while Selenium provides a browser-based fallback when the
primary fetcher fails or produces anomalous results. Gemini is used as
an extraction and normalization layer that converts unstructured crawled
content into the application's expected schema.

The live demonstration should use a low-risk source such as a public
job-board RSS/API or a sandbox controlled by the project owner.

## 2. High-Level Architecture

``` text
                         ┌─────────────────┐
                         │   Job Source    │
                         └────────┬────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │ Ingestion Scheduler │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │     Firecrawl       │
                       │   Primary Fetcher   │
                       │  Rate Limit / Retry │
                       └──────────┬──────────┘
                                  │
                   ┌──────────────┴──────────────┐
                   │                             │
               successful                    failure /
                   │                         anomaly
                   │                             │
                   │                             ▼
                   │                    ┌─────────────────┐
                   │                    │    Selenium     │
                   │                    │ Browser Fallback│
                   │                    └────────┬────────┘
                   │                             │
                   └──────────────┬──────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Raw Storage   │
                         │ HTML / Markdown │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Pre-processing  │
                         │ Dedup / Filter  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │     Gemini      │
                         │ Structured      │
                         │ Extraction      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Schema + Data   │
                         │ Validation      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   PostgreSQL    │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ API / Dashboard │
                         └─────────────────┘
```

Observability runs alongside the pipeline:

``` text
┌─────────────────────────────────────────────┐
│              Metrics / Logs                 │
│                                             │
│ Fetch success rate                          │
│ HTTP status distribution                    │
│ 429 / rate-limit count                      │
│ Fallback invocation count                   │
│ Extraction failures                         │
│ Jobs extracted / inserted                   │
│ Duplicate rate                              │
│ Parse anomaly rate                          │
│ Request latency                             │
└─────────────────────────────────────────────┘
```

## 3. Fetching Strategy

### 3.1 Primary Fetcher --- Firecrawl

Firecrawl is used as the primary ingestion mechanism because it reduces
the amount of custom browser automation required and provides a
convenient way to obtain page content for downstream processing.

The primary fetcher should use:

-   Request pacing
-   Configurable request limits
-   Timeouts
-   Retry handling
-   Exponential backoff
-   Source-specific request budgets
-   Detection of HTTP errors and unexpected responses

The goal is not to circumvent anti-bot protections. The system should
operate within the permissions and terms applicable to the selected
source.

### 3.2 Browser Fallback --- Selenium

Selenium provides a browser-based fallback when Firecrawl cannot
reliably retrieve the expected content.

Fallback conditions include:

-   HTTP/network failure
-   Timeout
-   Empty response
-   CAPTCHA or access challenge
-   Unexpected response structure
-   Significant drop in extracted content
-   Parser/extraction anomaly

The fallback should not be used to bypass authentication, CAPTCHA,
access controls, or other technical restrictions. If the source remains
unavailable, the system should back off and mark the source as unhealthy
rather than continuously retrying.

## 4. Failure Detection

A successful HTTP response does not necessarily mean a successful
ingestion.

For example:

``` text
Expected:
200 pages → 500 listings

Actual:
200 pages → 2 listings
```

The fetch operation technically succeeded, but the ingestion result is
anomalous.

The system should therefore validate both transport-level and
content-level success.

Example checks:

``` text
HTTP status      → expected
Response size    → reasonable
Content markers  → present
Listings found   → non-zero when expected
Listing count    → within historical range
Required fields  → present
```

If these checks fail, the result should be treated as a failed or
degraded ingestion and the fallback path may be invoked.

## 5. Raw Data Preservation

Raw crawled content should be stored before LLM extraction.

``` text
Crawler
   ↓
Raw HTML / Markdown
   ↓
Persistent Storage
   ↓
Gemini Extraction
```

This separation is important because extraction can be re-run without
crawling the source again.

For example, if the extraction prompt or Gemini model changes:

``` text
Stored Raw Data
      ↓
New Extraction Prompt
      ↓
Gemini
      ↓
New Structured Output
```

This improves reproducibility, debugging, and recovery from extraction
errors.

## 6. Pre-processing

Before sending data to Gemini, deterministic processing should be
performed where possible.

Recommended steps:

1.  Remove irrelevant page content.
2.  Identify individual listing boundaries.
3.  Normalize whitespace.
4.  Canonicalize URLs.
5.  Remove obvious duplicates.
6.  Compare against previously ingested records.
7.  Send only new or changed listings for LLM extraction where
    practical.

For example:

``` text
500 crawled listings
        ↓
Deduplication / filtering
        ↓
120 new or changed listings
        ↓
Gemini extraction
```

This reduces LLM cost, latency, and unnecessary processing.

## 7. Gemini Extraction Layer

Gemini is used as an unstructured-to-structured extraction layer.

The crawler may return content such as:

``` text
Software Engineer
Google
Bangalore
₹20-30 LPA
Posted 2 days ago
...
```

Gemini transforms this into a consistent schema:

``` json
{
  "title": "Software Engineer",
  "company": "Google",
  "location": "Bangalore",
  "salary": {
    "min": 2000000,
    "max": 3000000,
    "currency": "INR"
  },
  "posted_at": "...",
  "description": "...",
  "source": "..."
}
```

The LLM should be instructed to return structured output conforming to a
predefined schema.

Gemini should not be treated as the final validator. Its output must
pass deterministic schema and business validation before entering the
database.

## 8. Schema Validation

The processing flow should be:

``` text
Raw Crawl
    ↓
Gemini
    ↓
Schema Validation
    ↓
Business Validation
    ↓
Database
```

Example required fields:

``` text
title       → required
company     → required
source_url  → required
location    → optional
salary      → optional
description → optional
posted_at   → optional
```

If Gemini returns invalid data, the record should be rejected, flagged,
or sent for retry rather than silently inserted.

For example:

``` json
{
  "title": null,
  "company": "Example Company"
}
```

should fail validation if `title` is required.

## 9. Deduplication

The system should avoid storing the same job repeatedly.

A canonical identity can be constructed using the source and canonical
job URL:

``` text
job_id = hash(source + canonical_url)
```

For sources where URLs are unstable, a secondary fingerprint can be
created from normalized attributes such as:

``` text
company + title + location
```

Deduplication should happen before expensive LLM processing whenever
possible.

## 10. Resilience and Recovery

### 10.1 Rate Limiting

The ingestion system should maintain source-specific request budgets and
avoid uncontrolled concurrency.

When a rate-limit response such as HTTP 429 is received:

``` text
429
 ↓
Stop or reduce requests
 ↓
Exponential backoff
 ↓
Retry
 ↓
Persistent failure?
 ↓
Mark source unhealthy
```

The system should never respond to rate limiting by increasing request
volume.

### 10.2 Fallback Strategy

The source ingestion path is:

``` text
Firecrawl
    ↓
Failure / anomaly
    ↓
Selenium
    ↓
Success → continue
    ↓
Failure
    ↓
Cooldown + retry later
    ↓
Persistent failure → alert
```

This prevents one source failure from bringing down the entire pipeline.

### 10.3 Source Isolation

Each source should have an independent adapter:

``` text
                 Ingestion Engine
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    Source A        Source B        Source C
    Adapter         Adapter         Adapter
        │               │               │
      RSS              API             HTML
```

A markup change in Source A should therefore require changes only to the
Source A adapter rather than the entire ingestion system.

## 11. Markup Change Detection

HTML-based sources can change their markup without notice.

The system should detect this through:

-   Extraction count monitoring
-   Required-field validation
-   Response-size changes
-   Selector/parser failure rates
-   Historical comparison
-   Unexpected empty responses

Example:

``` text
Previous ingestion:
150 listings

Current ingestion:
0 listings

        ↓

Ingestion anomaly detected
        ↓
Do not mark run as successful
        ↓
Trigger fallback / alert
```

This prevents silent data loss.

## 12. Observability

The pipeline should expose operational metrics such as:

``` text
last_successful_ingestion
fetch_attempts
fetch_successes
fetch_failures
http_429_count
fallback_count
pages_processed
listings_extracted
listings_inserted
duplicates
schema_validation_failures
llm_extraction_failures
parse_anomalies
average_latency
```

A basic health view could look like:

``` text
Last successful ingestion: 21:05
Jobs fetched:              147
Jobs inserted:             103
Duplicates:                 44
HTTP 429s:                   0
Parse failures:              0
Fallback runs:               2
```

The important principle is that the system should distinguish between:

``` text
"Fetcher returned HTTP 200"
```

and:

``` text
"Ingestion successfully produced valid job data"
```

## 13. Detection Surface and Risk Management

Automated clients can potentially be identified through multiple
signals.

### Client-level signals

-   Browser characteristics
-   Headless-browser indicators
-   User-Agent and header consistency
-   Cookie/session behavior
-   JavaScript execution characteristics
-   Network and TLS characteristics
-   IP reputation

### Request-level signals

-   Very high request frequency
-   Excessive concurrency
-   Identical request intervals
-   Repeated requests for the same content
-   Unusual pagination behavior
-   Abnormally large amounts of data retrieved in a short period

### Session-level signals

-   Unusual session duration
-   Rapid session creation
-   Geographic inconsistencies
-   Large-scale access patterns
-   Authentication anomalies

The design addresses these risks primarily through conservative
ingestion behavior, source-specific budgets, retry/backoff policies,
session isolation where appropriate, and failure handling.

The design intentionally does not attempt to defeat CAPTCHA,
authentication, access controls, or other explicit anti-automation
mechanisms.

## 14. What Happens If the Primary Approach Is Shut Down?

The system should treat source availability as an operational dependency
rather than something that must be forcibly bypassed.

The recovery hierarchy is:

``` text
Primary permitted fetch mechanism
            ↓
Browser fallback where permitted
            ↓
Cooldown / exponential backoff
            ↓
Source health marked degraded
            ↓
Alternative permitted source
            ↓
Alert / operator intervention
```

The long-term Plan B is therefore not an increasingly aggressive evasion
mechanism. It is source diversification and adapter isolation.

For example:

``` text
Source A ── unavailable
Source B ── available
Source C ── available

            ↓

Pipeline continues using B and C
```

## 15. Where the System Stops

The technical boundary is explicit.

The system is designed to use:

-   Publicly accessible data
-   Official APIs
-   RSS feeds
-   Sources that permit automated access
-   A controlled sandbox for demonstration

The system does not attempt to:

-   Bypass CAPTCHA
-   Circumvent authentication
-   Defeat access controls
-   Access private or user-only information
-   Use compromised accounts
-   Deliberately evade platform restrictions
-   Increase scraping intensity after a source asks the client to slow
    down or stops serving the client

If a source blocks the ingestion process, the correct system behavior is
to back off, record the failure, and use a permitted fallback or
alternative source.

## 16. End-to-End Processing Flow

``` text
                 ┌─────────────────┐
                 │   Public Source │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │    Scheduler    │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │   Firecrawl     │
                 │ Primary Fetcher │
                 └────────┬────────┘
                          │
                ┌─────────┴─────────┐
                │                   │
             Success             Failure
                │                   │
                │                   ▼
                │             ┌─────────────┐
                │             │  Selenium   │
                │             └──────┬──────┘
                │                    │
                └──────────┬─────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Raw Storage │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Preprocess  │
                    │ + Dedup     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Gemini    │
                    │  Extraction │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Validation  │
                    └──────┬──────┘
                           │
                     ┌─────┴─────┐
                     │           │
                   Valid       Invalid
                     │           │
                     ▼           ▼
               ┌──────────┐   Retry / Flag
               │PostgreSQL│
               └────┬─────┘
                    │
                    ▼
               ┌──────────┐
               │ API / UI │
               └──────────┘
```

## 17. Key Design Decisions

### Firecrawl as the primary fetcher

Reduces custom browser automation and keeps the normal ingestion path
relatively simple.

### Selenium as a controlled fallback

Provides a browser-based recovery path when the primary fetching
mechanism cannot obtain the expected content.

### Gemini for extraction, not validation

LLMs are useful for converting heterogeneous content into a normalized
schema, but deterministic validation remains responsible for data
integrity.

### Raw data before LLM processing

Makes extraction reproducible and allows reprocessing without another
crawl.

### Source-specific adapters

Limits the impact of markup or API changes to individual sources.

### Backoff instead of aggressive retries

Prevents the ingestion system from escalating a temporary source problem
into a larger operational failure.

### Observability and anomaly detection

Prevents silent failures when a source changes its markup, returns
incomplete content, or begins rate-limiting requests.

## 18. Summary

The proposed architecture is a resilient ingestion pipeline rather than
a platform-specific scraping bypass.

Its core flow is:

``` text
Fetch
  ↓
Fallback if necessary
  ↓
Preserve raw data
  ↓
Pre-process / deduplicate
  ↓
LLM-based structured extraction
  ↓
Deterministic validation
  ↓
Persist
  ↓
Expose through API / UI
```

The system is designed to continue operating when individual requests
fail, when a source becomes temporarily unavailable, or when page
structure changes. It also has an explicit technical and ethical
boundary: it handles source failures through backoff, fallback, and
source diversification rather than attempting to defeat access controls.
