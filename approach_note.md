# Approach Note — Scaling & Hallucination Guardrails

## 1. Scaling from 3 pages to 10,000 pages
- **Concurrency:** replace the synchronous `requests.get` loop with an async
  worker pool (`aiohttp` + `asyncio`) bounded by a `Semaphore`; shard URLs and run
  N workers per host with per-domain rate limiting.
- **Rate-limiting & politeness:** a token-bucket limiter keyed by `netloc`
  (e.g. 1–2 req/s), exponential backoff on `429/503`, honour `Retry-After`, and a
  persistent `If-Modified-Since`/ETag cache to skip unchanged pages.
- **Anti-bot / Cloudflare:** rotate realistic User-Agents, use a pool of
  residential/rotating proxies, and for JS-heavy SPAs fall back to a headless
  renderer (Playwright/Splash) only when static HTML lacks the data. Route
  challenges to the renderer queue automatically.
- **Resilience:** retries with jitter, structured logging, a dead-letter queue for
  failed URLs, and checkpointed progress so a run resumes cleanly.
- **Storage:** stream extracted records to a message bus (Kafka) → warehousing;
  never hold 10k DOMs in memory.

## 2. Preventing LLM / extractor hallucinations
- **Strict schema enforcement:** Pydantic models for `University` and `Course`.
  Every extractor output is validated on ingest; unknown/extra fields are dropped
  and type violations rejected.
- **Post-extraction regex verification:** re-run the raw extraction regexes
  (`extract_fee`, date, currency) against the *original HTML*, not the model
  output. If a generated value cannot be located verbatim in the source, it is
  forced to `null`.
- **Null discipline as a contract:** validation asserts no `""`, `"N/A"`, or
  fabricated defaults; `Optional[...] = None` is the only empty state.
- **Provenance:** store `sourceUrl` + a content hash per record so any value is
  traceable and re-auditable, enabling automatic drift detection when markup
  changes.
