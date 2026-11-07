from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from digest_core.cache import JsonSourceCache
from digest_core.models import PipelinePaths, PipelineSettings
from pipeline.research_pipeline import ResearchDigestPipeline
from sources.dates import PublicationWindow, parse_publication_date
from sources.outcomes import SourceResult
from sources.retrieval import LiteratureRetriever, PaperSource
from sources import arxiv, chemrxiv, pubmed


NOW = datetime(2026, 4, 7, 12, tzinfo=timezone.utc)
PAPER = {"title": "Molecular docking benchmark", "abstract": "Drug discovery and virtual screening.",
         "url": "https://example.org/paper", "source": "fixture", "published": "2026-04-06"}


def fail(*args, **kwargs):
    raise RuntimeError("token=SECRET https://user:password@example.org/?api_key=PRIVATE")


def retriever(sources, **kwargs):
    return LiteratureRetriever(sources, reference_time=NOW, retry_attempts=1, **kwargs)


@pytest.mark.parametrize("published,reason", [
    ("2026-03-31T12:00:00Z", None), ("2026-04-07T12:00:00Z", None),
    ("2026-03-31T11:59:59Z", "before_window"), ("2026-04-07T12:00:01Z", "after_window"),
    ("2026-04-07T14:00:00+02:00", None), ("2026-03-31T14:00:00+02:00", None),
    ("2026-04-07", None), ("2026-03-31", "before_window"),
    (None, "missing"), ("", "missing"), ("not-a-date", "malformed"),
    ("2026-02-30", "malformed"), ("2026-04", "malformed"),
    ("2026-04-06T12:00:00", "ambiguous_timezone"),
])
def test_publication_window_policy(published, reason):
    records, rejected = PublicationWindow.recent(7, NOW).filter([{**PAPER, "published": published}])
    assert len(records) == (reason is None)
    assert rejected == ({reason: 1} if reason else {})
    if records:
        assert records[0]["published"].endswith("+00:00")
        assert records[0]["published_original"] == published


def test_reference_requires_timezone_and_date_only_is_midnight():
    with pytest.raises(ValueError):
        PublicationWindow.recent(7, datetime(2026, 4, 7))
    assert parse_publication_date("2026-04-06")[0] == datetime(2026, 4, 6, tzinfo=timezone.utc)


@pytest.mark.parametrize("papers,expected", [([PAPER], "success"), ([], "empty")])
def test_success_empty_and_list_compatibility(papers, expected):
    adapter_result = SourceResult(papers, source="fixture")
    assert isinstance(adapter_result, list)
    assert json.loads(json.dumps(adapter_result)) == papers
    r = retriever([PaperSource("fixture", lambda: adapter_result)])
    actual = r.fetch_all()
    assert isinstance(actual, list)
    assert len(actual) == len(papers)
    assert r.last_report["outcome"] == expected
    assert r.last_report["sources"][0]["outcome"] == expected


def test_partial_and_total_outage_are_explicit_and_errors_safe():
    r = retriever([PaperSource("healthy", lambda: [PAPER]), PaperSource("broken", fail)])
    assert len(r.fetch_all()) == 1
    assert r.last_report["outcome"] == "partial"
    broken = r.last_report["sources"][1]
    assert broken["outcome"] == "failed"
    assert broken["errors"] == [{"stage": "source.fetch", "error_type": "RuntimeError"}]
    assert "SECRET" not in json.dumps(r.last_report)
    r = retriever([PaperSource("broken", fail), PaperSource("also broken", fail)])
    assert r.fetch_all() == []
    assert r.last_report["outcome"] == "failed"


@pytest.mark.parametrize("papers", [[], [PAPER]])
def test_cache_hit_is_not_fresh_fetch_including_empty(tmp_path, papers):
    fetch = Mock(return_value=papers)
    r = retriever([PaperSource("fixture", fetch)], cache=JsonSourceCache(tmp_path))
    r.fetch_all()
    r.fetch_all()
    assert fetch.call_count == 1
    source = r.last_report["sources"][0]
    assert source["outcome"] == "cached"
    assert source["cache_usage"] == "fresh"
    assert source["cache_created_at"]


@pytest.mark.parametrize("stale", [False, True])
def test_cache_records_must_pass_current_window(tmp_path, stale):
    cache = JsonSourceCache(tmp_path)
    cache.set("fixture", [{**PAPER, "published": "2024-01-01"}])
    r = retriever([PaperSource("fixture", fail)], cache=cache, cache_ttl_hours=-1 if stale else 24)
    assert r.fetch_all() == []
    assert r.last_report["date_rejected_count"] == 1
    assert r.last_report["outcome"] == ("failed" if stale else "empty")
    assert r.last_report["sources"][0]["cache_usage"] == ("stale" if stale else "fresh")
    assert cache.get_stale("fixture").value[0]["published"] == "2024-01-01"


def test_adapter_failure_is_retried_and_does_not_replace_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("digest_core.cache.time.sleep", lambda _: None)
    cache = JsonSourceCache(tmp_path)
    cache.set("fixture", [PAPER])
    monkeypatch.setattr(pubmed.Entrez, "esearch", fail)
    fetch = Mock(side_effect=lambda: pubmed.fetch_pubmed_papers(reference_time=NOW))
    r = LiteratureRetriever([PaperSource("fixture", fetch)], cache=cache,
                            cache_ttl_hours=-1, reference_time=NOW, retry_attempts=2)
    assert len(r.fetch_all()) == 1
    assert fetch.call_count == 2
    source = r.last_report["sources"][0]
    assert source["outcome"] == "cached" and source["cache_usage"] == "stale"
    assert not source["completed"]
    assert len(source["errors"]) == 2
    assert source["errors"][0]["stage"] == "pubmed.search"
    assert r.last_report["outcome"] == "partial"
    assert cache.get_stale("fixture").value == [PAPER]


def test_one_window_is_passed_to_all_adapters():
    windows = []
    def fetch(window):
        windows.append(window)
        return []
    r = retriever([PaperSource("a", fetch, accepts_window=True), PaperSource("b", fetch, accepts_window=True)])
    r.fetch_all()
    assert windows[0] is windows[1]
    assert windows[0].end == NOW


def test_invalid_records_are_not_successful_empty_results():
    r = retriever([PaperSource("broken", lambda: [{"title": "", "url": "invalid"}])])
    assert r.fetch_all() == []
    assert r.last_report["outcome"] == "failed"
    assert r.last_report["sources"][0]["validation_rejected_count"] == 1


def test_errorless_failed_adapter_remains_visible_in_partial_batch():
    r = retriever([PaperSource("failed", lambda: SourceResult(completed=False)),
                   PaperSource("healthy", lambda: [PAPER])])
    r.fetch_all()
    assert r.last_report["outcome"] == "partial"


def test_failed_attempt_date_rejections_survive_retry(monkeypatch):
    monkeypatch.setattr("digest_core.cache.time.sleep", lambda _: None)
    fetch = Mock(side_effect=[SourceResult(completed=False, date_rejections={"before_window": 1}), [PAPER]])
    r = LiteratureRetriever([PaperSource("fixture", fetch)], reference_time=NOW, retry_attempts=2)
    r.fetch_all()
    assert r.last_report["date_rejected_count"] == 1
    assert r.last_report["outcome"] == "partial"


def feed(published, updated=""):
    return f'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Test</title>
    <entry><title>Molecular docking benchmark</title><summary>Virtual screening for drug discovery.</summary>
    <link href="https://chemrxiv.org/test"/>{published}{updated}</entry></feed>'''


def test_old_chemrxiv_feed_regression_and_updated_does_not_rescue_publication():
    result = chemrxiv._parse_feed_entries(feed("<published>2024-01-01T00:00:00Z</published>",
        "<updated>2026-04-07T12:00:00Z</updated>"), 7, reference_time=NOW)
    assert result == []
    assert result.date_rejections == {"before_window": 1}
    result = chemrxiv._parse_feed_entries(feed("", "<updated>2026-04-07T12:00:00Z</updated>"), 7, reference_time=NOW)
    assert result.date_rejections == {"missing": 1}


def test_chemrxiv_keeps_distinct_original_dates():
    result = chemrxiv._parse_feed_entries(feed("<published>2026-04-06T14:00:00+02:00</published>",
        "<updated>2026-04-07T12:00:00Z</updated>"), 7, reference_time=NOW)
    assert result[0]["published"] == "2026-04-06T12:00:00+00:00"
    assert result[0]["published_original"] == "2026-04-06T14:00:00+02:00"
    assert result[0]["updated"] == "2026-04-07T12:00:00Z"


def test_chemrxiv_all_routes_failed_and_partial_failure_visible(monkeypatch):
    monkeypatch.setattr(chemrxiv, "_fetch_feed_xml", fail)
    monkeypatch.setattr(chemrxiv, "_fetch_crossref_items", fail)
    result = chemrxiv.fetch_chemrxiv_papers(reference_time=NOW)
    assert result.outcome == "failed" and len(result.errors) == 3
    monkeypatch.setattr(chemrxiv, "_fetch_crossref_items", lambda *a, **k: [])
    result = chemrxiv.fetch_chemrxiv_papers(reference_time=NOW)
    assert result.outcome == "partial" and result.completed
    assert len(result.errors) == 2


def test_chemrxiv_parse_failure_preserves_usable_entries(monkeypatch):
    parsed = SimpleNamespace(version="atom10", bozo=True, bozo_exception=ValueError("secret"), entries=[
        {"title": PAPER["title"], "summary": PAPER["abstract"], "link": "https://chemrxiv.org/test",
         "published": PAPER["published"]}
    ])
    monkeypatch.setattr(chemrxiv.feedparser, "parse", lambda _: parsed)
    monkeypatch.setattr(chemrxiv, "_fetch_feed_xml", lambda _: "fixture")
    result = chemrxiv.fetch_chemrxiv_papers(reference_time=NOW)
    assert len(result) == 1 and result.outcome == "partial"
    assert not result.completed
    assert result.errors == [{"stage": "chemrxiv.feed_parse", "error_type": "ValueError"}]


def test_chemrxiv_successful_empty_routes_are_empty(monkeypatch):
    monkeypatch.setattr(chemrxiv, "_fetch_feed_xml", lambda _: '<rss version="2.0"><channel/></rss>')
    monkeypatch.setattr(chemrxiv, "_fetch_crossref_items", lambda *a, **k: [])
    result = chemrxiv.fetch_chemrxiv_papers(reference_time=NOW)
    assert result == [] and result.outcome == "empty" and not result.errors


@pytest.mark.parametrize("parts", [[2024, 1, 1], [2026, 4], [], [2026, 2, 30]])
def test_crossref_posted_date_does_not_replace_invalid_publication(monkeypatch, parts):
    monkeypatch.setattr(chemrxiv, "_fetch_crossref_items", lambda *a, **k: [{
        "title": ["Docking benchmark for ligand design"], "URL": PAPER["url"],
        "published": {"date-parts": [parts]}, "posted": {"date-parts": [[2026, 4, 6]]},
    }])
    result = chemrxiv._parse_crossref_entries(7, reference_time=NOW)
    assert result == [] and sum(result.date_rejections.values()) == 1


def test_arxiv_partial_stream_is_not_complete_success(monkeypatch):
    item = SimpleNamespace(title=PAPER["title"], summary=PAPER["abstract"], entry_id=PAPER["url"],
                           published=NOW - timedelta(days=1), updated=NOW, authors=[], pdf_url=None)
    def results(search):
        yield item
        fail()
    monkeypatch.setattr(arxiv.arxiv, "Client", lambda **kwargs: SimpleNamespace(results=results))
    result = arxiv.fetch_arxiv_papers(reference_time=NOW)
    assert len(result) == 1 and result.outcome == "partial" and not result.completed
    assert result[0]["published"] != result[0]["updated"]
    assert result.errors[0]["stage"] == "arxiv.results"


@pytest.mark.parametrize("published", [NOW - timedelta(days=8), NOW + timedelta(seconds=1), None])
def test_arxiv_temporal_gate(monkeypatch, published):
    item = SimpleNamespace(title=PAPER["title"], summary=PAPER["abstract"], entry_id=PAPER["url"],
                           published=published, updated=NOW, authors=[])
    monkeypatch.setattr(arxiv.arxiv, "Client", lambda **kwargs: SimpleNamespace(results=lambda _: [item]))
    result = arxiv.fetch_arxiv_papers(reference_time=NOW)
    assert not result and result.outcome == "empty"
    assert sum(result.date_rejections.values()) == 1


@pytest.mark.parametrize("date_xml", ["", "<Year>2026</Year><Month>4</Month>",
    "<Year>2024</Year><Month>1</Month><Day>1</Day>", "<MedlineDate>Spring 2026</MedlineDate>"])
def test_pubmed_missing_ambiguous_and_old_dates_rejected(monkeypatch, date_xml):
    monkeypatch.setattr(pubmed.Entrez, "esearch", lambda **k: object())
    monkeypatch.setattr(pubmed.Entrez, "read", lambda _: {"IdList": ["1"]})
    xml = f"<PubmedArticleSet><PubmedArticle><PMID>1</PMID><ArticleTitle>Title</ArticleTitle><Abstract><AbstractText>Abstract</AbstractText></Abstract><PubDate>{date_xml}</PubDate></PubmedArticle></PubmedArticleSet>"
    monkeypatch.setattr(pubmed.Entrez, "efetch", lambda **k: SimpleNamespace(read=lambda: xml))
    result = pubmed.fetch_pubmed_papers(reference_time=NOW)
    assert result == [] and result.outcome == "empty"
    assert sum(result.date_rejections.values()) == 1


@pytest.mark.parametrize("xml", ["<html/>", "<PubmedArticleSet/>"])
def test_pubmed_error_or_incomplete_response_is_not_empty_success(monkeypatch, xml):
    monkeypatch.setattr(pubmed.Entrez, "esearch", lambda **k: object())
    monkeypatch.setattr(pubmed.Entrez, "read", lambda _: {"IdList": ["1"]})
    monkeypatch.setattr(pubmed.Entrez, "efetch", lambda **k: SimpleNamespace(read=lambda: xml))
    result = pubmed.fetch_pubmed_papers(reference_time=NOW)
    assert result == [] and result.outcome == "failed" and result.errors


@pytest.mark.parametrize("outage", [True, False])
def test_pipeline_exposes_outage_vs_eligible_empty_without_publishing(tmp_path, monkeypatch, outage):
    monkeypatch.chdir(tmp_path)
    publisher = Mock()
    r = retriever([PaperSource("fixture", fail if outage else lambda: [])])
    pipeline = ResearchDigestPipeline(r, Mock(), publisher, PipelinePaths(), PipelineSettings(), Mock())
    result = pipeline.run()
    assert result.retrieval["outcome"] == ("failed" if outage else "empty")
    assert result.retrieval["sources"][0]["outcome"] == ("failed" if outage else "empty")
    publisher.publish.assert_not_called()
    pipeline.summarizer.assert_not_called()
    if outage:
        assert not (tmp_path / "data/raw_papers.json").exists()


def test_pipeline_retains_partial_health_after_publication(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = retriever([PaperSource("healthy", lambda: [PAPER]), PaperSource("broken", fail)])
    publisher = Mock()
    publisher.publish.return_value = "temporary.html"
    pipeline = ResearchDigestPipeline(r, SimpleNamespace(prepare=lambda papers: (papers, [])),
        publisher, PipelinePaths(), PipelineSettings(enable_cluster_selection=False),
        summarizer=lambda papers: papers, relevance_filter=lambda papers: papers,
        narrative_generator=lambda summaries: "")
    result = pipeline.run()
    assert result.weekly_post == "temporary.html"
    assert result.retrieval["outcome"] == "partial"
    assert result.retrieval["sources"][1]["errors"]
