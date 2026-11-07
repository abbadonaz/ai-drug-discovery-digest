# Retrieval health and publication windows (A04/A05)

Discovery now reports operational health separately from whether eligible papers exist. This change does not alter relevance scoring, clustering, summary generation, prompts, deployment, or atomic publication behavior.

## Compatibility and outcomes

The arXiv, PubMed and ChemRxiv fetch functions retain positional `days_back`/result-limit arguments and return `SourceResult`, a `list` subclass. Iteration, indexing, equality with lists and JSON serialization of papers still work. Each adapter accepts an optional keyword-only `reference_time`. Callers must inspect `.outcome` or `.diagnostics()` to distinguish failures from empty lists; plain JSON serialization of the list alone intentionally does not include diagnostics.

`LiteratureRetriever.fetch_all()` still returns a plain paper list. Its new `last_report` contains structured health for that call. Existing zero-argument `PaperSource.fetch` callables remain supported; production adapters opt into `accepts_window=True`, receiving the same `PublicationWindow` for every source in a run. Legacy callables that themselves swallow exceptions cannot be diagnosed automatically.

Source diagnostics:

| Field | Values/meaning |
| --- | --- |
| `source` | Configured source name |
| `outcome` | `success`, `empty`, `partial`, `failed`, `cached` |
| `paper_count` | Valid, temporally eligible records returned |
| `completed` | Whether acquisition completed; false for interrupted streams or failed fresh fetches even if stale cache supplies papers |
| `cache_usage` | `none`, `fresh` (within TTL), `stale` (fallback after failed fetch); neither cache mode denotes a fresh network fetch |
| `cache_created_at` | Original cache timestamp, or null |
| `errors` | Stage and exception type; numeric HTTP status when available. Exception messages, request URLs, credentials and response bodies are excluded |
| `date_rejected_count` | Sum of temporal rejection observations across this call's source attempts/cache read |
| `date_rejections` | Counts by `missing`, `malformed`, `ambiguous_timezone`, `before_window`, `after_window` |
| `validation_rejected_count` | Records rejected at the Pydantic source boundary |

`partial` retains usable interrupted results, failed fallback routes, recovered retry errors or invalid-record diagnostics. It may have zero papers if some acquisition completed but other routes failed. A complete acquisition with no eligible papers is `empty`, even when candidates were excluded by date. ChemRxiv preserves earlier route failures when a later route works. Rejection counts are observations, not deduplicated studies: retries/fallbacks can encounter the same record repeatedly.

Aggregate `last_report` fields are `outcome` (`success`, `empty`, `partial`, `failed`), `paper_count`, `window_start`, `window_end`, `date_rejected_count`, and `sources`. Cache status stays source-specific; aggregate `success` may include valid cached results. Degraded sources produce aggregate `partial`. All sources failed with no eligible fallback data produces `failed`.

`PipelineRunResult.retrieval` retains this report on normal, empty, no-featured-evidence and failed-discovery returns. Legacy retrievers without a report receive `{"outcome": "unknown"}`. A failed-discovery run stops before deduplication, JSON snapshot writes, summarization and publication. It does not erase an existing digest. Source and aggregate diagnostics are also emitted as structured log events. This commit does not change CLI exit policy, CI deployment gates or atomic output replacement (A06/A08).

## Date policy

The inclusive eligibility interval is `[reference_time - days_back, reference_time]`. `LiteratureRetriever` captures one timezone-aware reference time per `fetch_all()` invocation (UTC now unless injected) and passes its window to production adapters. Tests/replays inject an explicit reference time. Runtime lookback defaults to seven days and is configurable with `LITERATURE_DAYS_BACK`; `PipelineSettings.days_back` and the retriever's `days_back` remain available to programmatic callers. Direct adapter defaults are preserved.

- Aware ISO timestamps and RFC feed timestamps are normalized to UTC before comparison. Offsets are converted, never simply stripped.
- Exact date-only `YYYY-MM-DD` values are interpreted as **00:00:00 UTC** on that date. This is a documented precision convention, not a claim about the actual publication hour. A date on the lower-bound calendar day is excluded if its midnight precedes the exact rolling-window start.
- Missing dates, invalid dates, partial year/month/season dates, and timestamps without a timezone are rejected. Unknown dates never become today. Existing legacy cache records with naive timestamps are therefore ineligible until refreshed from authoritative metadata.
- Publication and update dates are distinct. arXiv retains `updated`; feed records retain actual `updated` without feedparser's compatibility alias. PubMed retains raw `DateRevised` parts as `updated_original`. Updates never rescue old/missing publications. Crossref `posted` is retained as `posted_original`, not silently substituted for `published`.
- PubMed requires a complete publication year/month/day; ambiguous `MedlineDate` ranges are excluded. Crossref requires complete three-part publication dates. Source-provided malformed or incomplete parts remain available in raw metadata before exclusion.
- Accepted papers preserve existing fields, add `published_original`, and normalize `published` to UTC ISO format. PubMed/Crossref also retain `publication_date_original` components. Rejected paper payloads are not persisted; their reason counts are exposed.

All adapters use `PublicationWindow.filter()`. The retriever reapplies it to every accepted fresh or cached record, including stale fallback records. Crossref request bounds derive from the same window, followed by the exact local gate. No source uses the newest returned paper as an implicit reference date.

## Cache/retry behavior and limits

The existing TTL, stale fallback and outer retry count/backoff remain. Explicit failed adapter results now trigger retries, as raised exceptions already did. Partial responses retain diagnostic errors and are not cached over a known-good snapshot. Successful empty results are cached and recognized as valid cache hits. Invalid records make a result partial (or failed if all records are invalid) rather than silently treating malformed responses as successful empty searches.

Stale cache fallback remains available after a failed fetch, but only eligible papers can be used. If a stale cache is empty or all its records are ineligible, the fresh outage remains `failed`, with stale-cache metadata and rejections retained. Cache files are not overwritten on source failure. Malformed cache timestamps and non-list payloads are ignored; old valid cache JSON remains readable.

Remaining limits: source result limits/pagination may undercount literature; parser heuristics and API availability remain source-specific. Source cache keys still do not fingerprint queries/lookback changes, so changing configuration can require clearing the source cache or waiting for TTL expiry to discover additional records. No new maximum stale-cache age was introduced; publication eligibility is enforced independently of cache age. Diagnostics currently survive in run results/logs, not a durable run manifest. No scientific completeness or factual-validity guarantee is implied.

## Validation for this commit

- `.venv\Scripts\python.exe -m pytest -q tests/test_source_health_and_dates.py tests/test_retrieval_cache.py tests/test_fetch_chemrxiv.py tests/test_fetchers_and_rendering.py`: **67 passed**.
- `.venv\Scripts\python.exe -m pytest -q`: **235 passed in 25.82 s**.
- Existing source test fixtures now inject fixed reference times and actual publication dates. The invalid-record cache test intentionally now expects a partial result not to overwrite/cache a healthy-looking snapshot. No external requests are required by these tests.
- The existing untracked `docs/audit/baseline.py` was run via `runpy` with `PYTHONHASHSEED=0`, `HF_HUB_OFFLINE=1`, and an in-process patch injecting `reference_time=2026-08-29T23:59:59Z` into `LiteratureRetriever.__init__`. The audit script/artifacts were not edited. This explicit historical replay is necessary because the saved snapshot is not a current literature batch. It used the script's existing socket/inference blocks and temporary output directory.
- Historical replay: 12 eligible of 55 records, nine relevance-filtered, two featured, two brief; temporary HTML generated. Rejections were one before-window, one after-window and 41 ambiguous timezone records. The full source report survived in `PipelineRunResult.retrieval`; the old-feed probe accepted **zero** records.
- A separate shared-window check at `2026-11-07T00:00:00Z` accepted zero saved records: 13 before-window, one after-window and 41 ambiguous timezone records. These exclusions are intentional temporal-policy changes, not scientific ranking regressions. The baseline's publication filename still uses the local execution date, as before; this commit does not change publication scheduling.

Production data and existing audit outputs were not overwritten. No live source/API or hosted deployment verification was performed.
