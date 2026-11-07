from datetime import datetime, timezone

from digest_core.cache import JsonSourceCache
from digest_core.logging import NullRunLogger
from sources.retrieval import LiteratureRetriever, PaperSource


def test_retriever_validates_records_without_caching_partial_results(tmp_path):
    cache = JsonSourceCache(tmp_path)
    calls = []

    def fetch():
        calls.append(1)
        return [
            {
                "title": "Docking benchmark",
                "abstract": "Virtual screening for drug discovery.",
                "url": "https://example.org/paper",
                "source": "fixture",
                "published": "2026-04-06",
            },
            {"title": "", "url": "not-a-url", "source": "fixture"},
        ]

    retriever = LiteratureRetriever(
        [PaperSource("Fixture", fetch, cache_key="fixture")],
        cache=cache,
        reference_time=datetime(2026, 4, 7, tzinfo=timezone.utc),
        logger=NullRunLogger(),
    )

    assert len(retriever.fetch_all()) == 1
    assert len(retriever.fetch_all()) == 1
    assert len(calls) == 2
    assert retriever.last_report["outcome"] == "partial"
    assert retriever.last_report["sources"][0]["validation_rejected_count"] == 1


def test_retriever_uses_stale_cache_after_source_failure(tmp_path):
    cache = JsonSourceCache(tmp_path)
    cache.set("fixture", [{
        "title": "Cached paper",
        "abstract": "Cached abstract.",
        "url": "https://example.org/cached",
        "source": "fixture",
        "published": "2026-04-06",
    }])

    def fetch():
        raise RuntimeError("network failed")

    retriever = LiteratureRetriever(
        [PaperSource("Fixture", fetch, cache_key="fixture")],
        cache=cache,
        reference_time=datetime(2026, 4, 7, tzinfo=timezone.utc),
        cache_ttl_hours=-1,
        retry_attempts=1,
        logger=NullRunLogger(),
    )

    papers = retriever.fetch_all()

    assert papers[0]["title"] == "Cached paper"
