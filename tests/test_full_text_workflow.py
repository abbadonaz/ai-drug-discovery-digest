import json
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace

import pytest
import requests

from evidence import full_text
from evidence.pipeline import EvidenceBuilderDependencies, FeaturedPaperEvidenceBuilder
from evidence.pdf_extract import extract_pdf_text
from evidence.pdf_sections import extract_sections, build_paper_context
from evidence.selector import build_summary_payload
from summarization.scientific_summary import summarize_scientific, validate_sections, SECTIONS, NOT_ESTABLISHED
from summarization.ollama_client import ChatText
from web.digest import _render_summary_modes


PDF = Path(__file__).parent / "fixtures/evidence/scientific-study.pdf"
PAPER = {"title": "Synthetic", "url": "https://arxiv.org/abs/1234.56789v1", "abstract":
         "This molecular model predicts properties using graph descriptors and retrospective validation. "
         "The study compares prediction performance against a baseline on a scaffold split. "
         "No experimental binding measurements were reported in the available abstract."}


def builder(retrieval, **kwargs):
    deps = EvidenceBuilderDependencies(download_pdf=lambda p: None, extract_pdf_text=extract_pdf_text,
        extract_sections=extract_sections, build_paper_context=build_paper_context,
        rank_sentences=lambda values, top_k: values, retrieve_full_text=lambda p: retrieval)
    return FeaturedPaperEvidenceBuilder(deps, strategy="section_aware", summary_format="scientific_sections", **kwargs)


def test_routes_cache_and_identity(tmp_path):
    calls = []
    def fetch(url, limit):
        calls.append(url)
        return PDF.read_bytes(), url
    result = full_text.retrieve_full_text(PAPER, tmp_path, fetch)
    assert result["outcome"] == "success" and result["document_id"]
    assert calls == ["https://arxiv.org/pdf/1234.56789v1"]
    cached = full_text.retrieve_full_text(PAPER, tmp_path, fetch)
    assert cached["outcome"] == "cached" and len(calls) == 1
    Path(result["path"]).write_bytes(b"corrupt")
    assert full_text.retrieve_full_text(PAPER, tmp_path, fetch)["outcome"] == "success"
    assert len(calls) == 2


@pytest.mark.parametrize("content", [b"<html>landing</html>", b"", b"login required"])
def test_non_pdf_is_not_cached(tmp_path, content):
    result = full_text.retrieve_full_text(PAPER, tmp_path, lambda url, limit: (content, url))
    assert result["outcome"] == "failed"
    assert result["reason"] == "not_pdf"
    assert not list(tmp_path.iterdir())


def test_access_denied_and_no_route(tmp_path):
    def denied(url, limit):
        raise requests.HTTPError(response=SimpleNamespace(status_code=403))
    result = full_text.retrieve_full_text(PAPER, tmp_path, denied)
    assert result["reason"] == "access_denied"
    unknown = full_text.retrieve_full_text({"url": "https://example.org/landing"}, tmp_path, denied)
    assert unknown["outcome"] == "unavailable"


def test_chemrxiv_and_pmc_routes(tmp_path):
    paper = {"url": "https://chemrxiv.org/doi/full/10.26434/test/v1"}
    assert full_text.pdf_routes(paper) == ["https://chemrxiv.org/doi/pdf/10.26434/test/v1"]
    def fetch(url, limit):
        if "idconv" in url:
            return b'{"records":[{"pmcid":"PMC123"}]}', url
        if "list-type" in url:
            return b'<ListBucketResult><Contents><Key>metadata/PMC123.2.json</Key></Contents></ListBucketResult>', url
        return b'{"pdf_url":"https://pmc-oa-opendata.s3.amazonaws.com/PMC123.2/a.pdf","license_code":"CC-BY","version":2,"is_manuscript":"no"}', url
    assert full_text.pmc_routes({"url": "https://pubmed.ncbi.nlm.nih.gov/123/"}, fetch)[0].endswith("a.pdf")
    def metadata(url, limit):
        if url.endswith("/landing"):
            return b'<meta name="citation_pdf_url" content="/asset.pdf">', url
        return PDF.read_bytes(), url
    assert full_text.retrieve_full_text({"url":"https://chemrxiv.org/landing"}, tmp_path, metadata)["outcome"] == "success"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1/a", "https://user:secret@arxiv.org/pdf/1", "https://arxiv.org:9000/a", "https://evil.example/a", "https://arxiv.org/\na"])
def test_unsafe_urls_rejected(url):
    with pytest.raises(ValueError):
        full_text.validate_url(url)


def test_private_dns_and_redirect_download_limits(monkeypatch):
    monkeypatch.setattr(full_text.socket, "getaddrinfo", lambda *a: [(0,0,0,'',('127.0.0.1',443))])
    with pytest.raises(ValueError, match="nonpublic"):
        full_text.validate_url("https://arxiv.org/pdf/a")
    monkeypatch.setattr(full_text, "validate_url", lambda url: None)
    class Response:
        status_code = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_content(self, n): yield b"123456"
    session = SimpleNamespace(get=lambda *a, **kw: Response())
    with pytest.raises(ValueError, match="download_limit"):
        full_text.fetch_bytes("https://arxiv.org/pdf/a", 5, session)
    Response.status_code = 302
    Response.headers = {"Location": "https://arxiv.org/again"}
    with pytest.raises(ValueError, match="redirect_limit"):
        full_text.fetch_bytes("https://arxiv.org/pdf/a", 5, session)


def test_fulltext_structured_generation_model_and_provenance():
    paper = builder({"path": str(PDF), "outcome": "cached", "document_id": "test"}).build_featured_record(PAPER)
    payload = build_summary_payload(paper)
    evidence = payload["evidence"]
    response = {key: {"text": NOT_ESTABLISHED, "passage_ids": []} for key in SECTIONS}
    method = next(p for p in evidence if p["section"] == "training_validation")
    response["methodology"] = {"text": method["text"], "passage_ids": [method["passage_id"]]}
    prompts = []
    def chat(prompt, **kwargs):
        prompts.append(prompt)
        return ChatText(json.dumps(response), "test-model", {"temperature": .2, "num_predict":900})
    summary = summarize_scientific(paper, chat)
    assert summary["generation_mode"] == "llm"
    assert summary["model_identity"] == "test-model"
    assert summary["summary_evidence_mode"] == "pdf_full_text"
    assert len(summary["scientific_sections"]) == 6
    assert all(p["text"] in prompts[0] for p in evidence)
    assert all(c["support_status"] == "unverified" for c in summary["provenance"])
    assert summary["scientific_sections"]["quantitative_findings"]["text"] == NOT_ESTABLISHED


def test_invalid_numbers_and_ids_not_accepted():
    paper = builder({"path": str(PDF), "outcome": "cached"}).build_featured_record(PAPER)
    evidence = build_summary_payload(paper)["evidence"]
    result = {key: {"text": NOT_ESTABLISHED, "passage_ids": []} for key in SECTIONS}
    result["quantitative_findings"] = {"text": "RMSE was 99999.42 nM.", "passage_ids": [evidence[0]["passage_id"]]}
    checked, issues = validate_sections(json.dumps(result), evidence)
    assert checked["quantitative_findings"]["text"] == NOT_ESTABLISHED and issues
    result["methodology"] = {"text":"Invented", "passage_ids":["invented"]}
    checked, issues = validate_sections(json.dumps(result), evidence)
    assert checked["methodology"] == {"text": NOT_ESTABLISHED, "passage_ids": []}
    assert {"section": "methodology", "reason": "unknown_passage_reference"} in issues


@pytest.mark.parametrize("status", ["failed", "unavailable"])
def test_abstract_policy_and_generation_fallback(status):
    retrieval = {"path": None, "outcome":status, "reason":"access_denied"}
    paper = builder(retrieval).build_featured_record(dict(PAPER))
    def blocked(*args, **kwargs): raise RuntimeError("offline")
    result = summarize_scientific(paper, blocked)
    assert result["generation_mode"] == "extractive_fallback"
    assert result["summary_evidence_mode"] == "abstract_only"
    assert result["full_text_fallback_reason"] == "retrieval_" + status
    assert "not a comprehensive article review" in _render_summary_modes(result)
    from evidence.pipeline import make_brief_record
    candidate = dict(PAPER)
    assert builder(retrieval, fallback_policy="brief_only").build_featured_record(candidate) is None
    assert make_brief_record(candidate)["full_text_fallback_reason"] == "retrieval_" + status


def test_parsing_failure_is_distinct(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("bad")
    record = builder({"path":str(bad), "outcome":"success"}).build_featured_record(PAPER)
    assert record["full_text_fallback_reason"] == "extraction_failed"
