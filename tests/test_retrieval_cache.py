from digest_core.cache import JsonSourceCache
from digest_core.logging import NullRunLogger
from sources.retrieval import LiteratureRetriever, PaperSource


def test_retriever_validates_and_caches_source_records(tmp_path):
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
            },
            {"title": "", "url": "not-a-url", "source": "fixture"},
        ]

    retriever = LiteratureRetriever(
        [PaperSource("Fixture", fetch, cache_key="fixture")],
        cache=cache,
        logger=NullRunLogger(),
    )

    assert len(retriever.fetch_all()) == 1
    assert len(retriever.fetch_all()) == 1
    assert len(calls) == 1


def test_retriever_uses_stale_cache_after_source_failure(tmp_path):
    cache = JsonSourceCache(tmp_path)
    cache.set("fixture", [{
        "title": "Cached paper",
        "abstract": "Cached abstract.",
        "url": "https://example.org/cached",
        "source": "fixture",
    }])

    def fetch():
        raise RuntimeError("network failed")

    retriever = LiteratureRetriever(
        [PaperSource("Fixture", fetch, cache_key="fixture")],
        cache=cache,
        cache_ttl_hours=-1,
        retry_attempts=1,
        logger=NullRunLogger(),
    )

    papers = retriever.fetch_all()

    assert papers[0]["title"] == "Cached paper"
