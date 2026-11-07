from collections import Counter
from dataclasses import dataclass
from typing import Callable

from pydantic import ValidationError

from digest_core.cache import JsonSourceCache, retry_call
from digest_core.logging import NullRunLogger
from digest_core.models import PaperRecord
from sources.dates import PublicationWindow
from sources.outcomes import SourceResult, eligible_result, error_diagnostic


PaperFetcher = Callable[..., list[dict]]


@dataclass(frozen=True)
class PaperSource:
    name: str
    fetch: PaperFetcher
    cache_key: str | None = None
    accepts_window: bool = False


class _SourceFailed(Exception):
    pass


class LiteratureRetriever:
    def __init__(self, sources: list[PaperSource], cache: JsonSourceCache | None = None,
                 cache_ttl_hours: int = 24, retry_attempts: int = 2, logger=None,
                 *, days_back=7, reference_time=None):
        self.sources = sources
        self.cache = cache
        self.cache_ttl_hours = cache_ttl_hours
        self.retry_attempts = retry_attempts
        self.logger = logger or NullRunLogger()
        self.days_back = days_back
        self.reference_time = reference_time
        self.last_report = None

    def fetch_all(self) -> list[dict]:
        window = PublicationWindow.recent(self.days_back, self.reference_time)
        results = [self._fetch_source(source, window) for source in self.sources]
        papers = [paper for result in results for paper in result]
        failed = sum(result.outcome == "failed" for result in results)
        degraded = any(result.errors or result.outcome in {"partial", "failed"} or not result.completed for result in results)
        status = ("failed" if results and failed == len(results) else
                  "partial" if degraded else "success" if papers else "empty")
        self.last_report = {
            "outcome": status, "paper_count": len(papers),
            "window_start": window.start.isoformat(), "window_end": window.end.isoformat(),
            "date_rejected_count": sum(sum(result.date_rejections.values()) for result in results),
            "sources": [result.diagnostics() for result in results],
        }
        self.logger.info("retrieval", "completed", **self.last_report)
        return papers

    def _validate_source_records(self, source_name, raw_papers):
        validated, rejected = [], 0
        for raw in raw_papers:
            try:
                paper = PaperRecord.model_validate({**raw, "source": raw.get("source") or source_name})
                validated.append(paper.to_dict())
            except (ValidationError, TypeError, AttributeError):
                rejected += 1
        return validated, rejected

    def _fetch_source(self, source, window):
        key = source.cache_key or source.name.lower()
        timer = self.logger.timer(f"source.{key}")
        errors = []
        failed_date_rejections = Counter()

        def prepare(raw, *, cache_usage="none", created_at=None):
            validated, rejected = self._validate_source_records(source.name, raw)
            result = eligible_result(validated, window, source=source.name,
                                     errors=errors + getattr(raw, "errors", []),
                                     completed=getattr(raw, "completed", True))
            result.date_rejections = dict(Counter(result.date_rejections) + Counter(getattr(raw, "date_rejections", {})) + failed_date_rejections)
            result.validation_rejected = rejected
            if rejected:
                result.errors.append({"stage": "source.validation", "error_type": "InvalidRecord"})
                if not validated:
                    result.completed = False
            result.cache_usage = cache_usage
            result.cache_created_at = created_at
            return result

        def fetch():
            try:
                raw = source.fetch(window) if source.accepts_window else source.fetch()
                if not isinstance(raw, list):
                    raise TypeError("Source must return a list-compatible result")
                if isinstance(raw, SourceResult) and raw.outcome == "failed":
                    errors.extend(raw.errors or [{"stage": "source.fetch", "error_type": "IncompleteResponse"}])
                    failed_date_rejections.update(raw.date_rejections)
                    raise _SourceFailed()
                return raw
            except _SourceFailed:
                raise
            except Exception as error:
                errors.append(error_diagnostic("source.fetch", error))
                raise

        cached = self.cache.get(key, ttl_hours=self.cache_ttl_hours) if self.cache else None
        if cached is not None:
            result = prepare(cached.value, cache_usage="fresh", created_at=cached.created_at.isoformat())
        else:
            try:
                raw = retry_call(fetch, attempts=self.retry_attempts)
            except Exception:
                stale = self.cache.get_stale(key) if self.cache else None
                result = prepare(stale.value, cache_usage="stale", created_at=stale.created_at.isoformat()) if stale else SourceResult(source=source.name, completed=False, errors=errors, date_rejections=failed_date_rejections)
                # Stale empty/ineligible records cannot establish fresh emptiness.
                result.completed = False
            else:
                result = prepare(raw)
                if self.cache and result.completed and not result.errors:
                    self.cache.set(key, list(result))
        timer.finish(**result.diagnostics())
        return result
