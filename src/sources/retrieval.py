from dataclasses import dataclass
from typing import Callable

from pydantic import ValidationError

from digest_core.cache import JsonSourceCache, retry_call
from digest_core.logging import NullRunLogger
from digest_core.models import PaperRecord


PaperFetcher = Callable[[], list[dict]]


@dataclass(frozen=True)
class PaperSource:
    name: str
    fetch: PaperFetcher
    cache_key: str | None = None


class LiteratureRetriever:
    def __init__(
        self,
        sources: list[PaperSource],
        cache: JsonSourceCache | None = None,
        cache_ttl_hours: int = 24,
        retry_attempts: int = 2,
        logger=None,
    ):
        self.sources = sources
        self.cache = cache
        self.cache_ttl_hours = cache_ttl_hours
        self.retry_attempts = retry_attempts
        self.logger = logger or NullRunLogger()

    def fetch_all(self) -> list[dict]:
        papers = []

        for source in self.sources:
            source_papers = self._fetch_source(source)
            papers.extend(source_papers)

        return papers

    def _fetch_source(self, source: PaperSource) -> list[dict]:
        cache_key = source.cache_key or source.name.lower()
        timer = self.logger.timer(f"source.{cache_key}")

        cached = self.cache.get(cache_key, ttl_hours=self.cache_ttl_hours) if self.cache else None
        if cached and cached.is_available:
            validated = self._validate_source_records(source.name, cached.value)
            timer.finish(count=len(validated), cache="hit")
            return validated

        try:
            raw_papers = retry_call(source.fetch, attempts=self.retry_attempts)
            validated = self._validate_source_records(source.name, raw_papers)
            if self.cache:
                self.cache.set(cache_key, validated)
            timer.finish(count=len(validated), cache="miss")
            return validated
        except Exception as error:
            stale = self.cache.get_stale(cache_key) if self.cache else None
            if stale and stale.is_available:
                validated = self._validate_source_records(source.name, stale.value)
                timer.finish(count=len(validated), cache="stale", error=str(error))
                return validated

            self.logger.error(f"source.{cache_key}", "failed", error=str(error))
            timer.finish(count=0, cache="unavailable")
            return []

    def _validate_source_records(self, source_name: str, raw_papers: list[dict]) -> list[dict]:
        validated = []

        for raw_paper in raw_papers or []:
            try:
                paper = PaperRecord.model_validate({**raw_paper, "source": raw_paper.get("source") or source_name})
            except ValidationError as error:
                self.logger.warning(
                    "source.validation",
                    "paper_rejected",
                    source=source_name,
                    title=raw_paper.get("title", ""),
                    error=str(error),
                )
                continue
            validated.append(paper.to_dict())

        return validated
