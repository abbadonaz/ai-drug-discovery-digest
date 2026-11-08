import json
from pathlib import Path

import pytest

from digest_core.models import PipelinePaths, PipelineSettings, SummaryRecord
from evidence.pipeline import EvidenceBuilderDependencies, FeaturedPaperEvidenceBuilder
from evidence.provenance import build_summary_provenance
from pipeline.research_pipeline import ResearchDigestPipeline
from summarization import llm
from web.digest import generate_digest_html
from web.publishing import DigestPublisher


PAPER = {"title": "Example paper", "url": "https://example.org/paper", "topic": "Other"}
ABSTRACT = (
    "This study develops a molecular screening workflow to investigate candidate compounds. "
    "The method uses a molecular representation for ranking candidates in a benchmark. "
    "The results describe model evaluation on the available dataset."
)


def fail(*args, **kwargs):
    raise RuntimeError("Deliberate test failure")


@pytest.fixture
def payload(monkeypatch):
    value = {
        **PAPER, "summary_input": ABSTRACT, "context": ABSTRACT,
        "evidence": [{"summary_role": "overview", "section": "abstract", "text": ABSTRACT}],
    }
    monkeypatch.setattr(llm, "build_summary_payload", lambda paper: value)
    monkeypatch.setattr(llm, "ENABLE_SUMMARY_QA", False)
    return value


def test_unsupported_claim_association_is_unverified():
    claims = build_summary_provenance("This treatment cures all diseases.", [
        {"summary_role": "overview", "section": "abstract", "text": "We study molecular representations."}
    ])
    assert claims[0]["support_status"] == "unverified"
    assert claims[0]["evidence"][0]["text"] == "We study molecular representations."
    assert claims[0]["claim"] == "This treatment cures all diseases."


@pytest.mark.parametrize("status", [None, "unverified", "verified", "supported"])
def test_rendering_never_claims_verification_and_escapes_passages(status):
    claim = {"claim": "Unsupported <script>claim</script>", "evidence": [
        {"section": "<b>abstract</b>", "text": "A <script>passage</script>."}
    ]}
    if status is not None:
        claim["support_status"] = status
    html = generate_digest_html([{**PAPER, "tldr": "**Summary** text.", "provenance": [claim]}], "")
    assert "Candidate source passages" in html
    assert "Support status: Unverified" in html
    assert "Support status: Verified" not in html
    assert "Evidence trace" not in html
    assert "&lt;script&gt;claim&lt;/script&gt;" in html
    assert "&lt;script&gt;passage&lt;/script&gt;" in html
    assert "&lt;b&gt;abstract&lt;/b&gt;" in html
    assert "<strong>Summary</strong>" in html
    assert 'href="https://example.org/paper"' in html
    assert "Summary generation: Unknown" in html
    assert "Evidence available: Unknown" in html


@pytest.mark.parametrize("mode", ["pdf_full_text", "abstract_only", "unknown"])
def test_llm_success_retains_known_evidence_mode(payload, monkeypatch, mode):
    monkeypatch.setattr(llm, "summarize_with_llm", lambda *args: "We study molecular representations. We evaluate a screening workflow.")
    record = llm.summarize_paper_record({**PAPER, "evidence_mode": mode})
    assert record["generation_mode"] == "llm"
    assert record["evidence_mode"] == mode
    assert all(claim["support_status"] == "unverified" for claim in record["provenance"])
    assert isinstance(llm.summarize_paper(PAPER), str)


@pytest.mark.parametrize("failure", ["exception", "invalid", "empty_input", "qa_exception"])
def test_actual_extractive_fallback_modes(payload, monkeypatch, failure):
    monkeypatch.setattr(llm, "summarize_with_llm", fail if failure == "exception" else lambda *args: "Incomplete")
    if failure == "empty_input":
        payload["summary_input"] = ""
    if failure == "qa_exception":
        monkeypatch.setattr(llm, "summarize_with_llm", lambda *args: "We study molecular representations. We evaluate a screening workflow.")
        monkeypatch.setattr(llm, "ENABLE_SUMMARY_QA", True)
        monkeypatch.setattr(llm, "hallucination_check", fail)
    record = llm.summarize_papers([{**PAPER, "evidence_mode": "abstract_only"}])[0]
    assert record["generation_mode"] == "extractive_fallback"
    assert record["evidence_mode"] == "abstract_only"
    assert "Extractive fallback" in generate_digest_html([record], "")


@pytest.mark.parametrize("verdict", ["VALID", "POTENTIAL_HALLUCINATION"])
def test_optional_qa_does_not_verify_claims(payload, monkeypatch, verdict):
    monkeypatch.setattr(llm, "ENABLE_SUMMARY_QA", True)
    monkeypatch.setattr(llm, "summarize_with_llm", lambda *args: "We study molecular representations. We evaluate a screening workflow.")
    monkeypatch.setattr(llm, "hallucination_check", lambda *args: verdict)
    record = llm.summarize_paper_record(PAPER)
    assert record["generation_mode"] == "llm"
    assert all(claim["support_status"] == "unverified" for claim in record["provenance"])


def test_no_source_placeholder_is_not_called_extractive(payload):
    payload.update(summary_input="", context="", evidence=[])
    record = llm.summarize_paper_record(PAPER)
    assert record["generation_mode"] == "unavailable"
    assert record["evidence_mode"] == "unknown"


@pytest.mark.parametrize("fallback_fails", [False, True])
def test_outer_batch_fallback_modes(payload, monkeypatch, fallback_fails):
    monkeypatch.setattr(llm, "summarize_paper_record", fail)
    if fallback_fails:
        monkeypatch.setattr(llm, "_extractive_fallback_result", fail)
    record = llm.summarize_papers([{**PAPER, "evidence_mode": "pdf_full_text"}])[0]
    assert record["generation_mode"] == ("unavailable" if fallback_fails else "extractive_fallback")
    assert record["evidence_mode"] == "pdf_full_text"


@pytest.mark.parametrize("case,expected", [
    ("missing_pdf", "abstract_only"), ("empty_pdf", "abstract_only"),
    ("full_text", "pdf_full_text"), ("pdf_abstract", "abstract_only"),
    ("rejected_pdf", "abstract_only"),
])
def test_evidence_mode_comes_from_preparation_path(case, expected):
    sections = {"abstract": ABSTRACT}
    if case in {"full_text", "rejected_pdf"}:
        sections["results"] = "Results from PDF."
    dependencies = EvidenceBuilderDependencies(
        download_pdf=lambda paper: None if case == "missing_pdf" else "paper.pdf",
        extract_pdf_text=lambda path: "" if case == "empty_pdf" else "PDF text",
        extract_sections=lambda text: dict(sections),
        build_paper_context=lambda sections: " ".join(sections.values()),
        rank_sentences=lambda sentences, top_k: sentences,
        evidence_validator=lambda record: not (case == "rejected_pdf" and "results" in record["sections"]),
    )
    record = FeaturedPaperEvidenceBuilder(dependencies).build_featured_record({**PAPER, "abstract": ABSTRACT})
    assert record["evidence_mode"] == expected


def test_modes_survive_ranking_persistence_and_publishing(payload, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(llm, "summarize_with_llm", fail)
    paths = PipelinePaths()
    pipeline = ResearchDigestPipeline(
        retriever=None, evidence_pipeline=None, publisher=DigestPublisher(paths),
        paths=paths, settings=PipelineSettings(), summarizer=llm.summarize_papers,
    )
    featured = [{**PAPER, "evidence_mode": "pdf_full_text"}]
    summaries = pipeline._summarize_and_rank(featured, [{**PAPER, "url": "https://example.org/brief"}])
    from digest_core.utils import save_json, load_json
    save_json(summaries, paths.summaries)
    loaded = load_json(paths.summaries)
    assert loaded[0]["generation_mode"] == "extractive_fallback"
    assert loaded[0]["evidence_mode"] == "pdf_full_text"
    assert loaded[1]["generation_mode"] == "not_generated"
    assert loaded[1]["evidence_mode"] == "unknown"
    pipeline.publisher.ensure_dirs()
    post = Path(pipeline.publisher.publish(loaded, ""))
    html = post.read_text(encoding="utf-8")
    assert "Summary generation: Extractive fallback" in html
    assert "Evidence available: PDF/full text available" in html
    assert "Not generated (reference only)" in html
    assert "Support status: Unverified" in html
    pipeline.summarizer = fail
    failed = pipeline._summarize_and_rank(featured, [])[0]
    assert failed["generation_mode"] == "unavailable"
    assert failed["evidence_mode"] == "pdf_full_text"


def test_saved_legacy_json_is_readable_without_inferred_modes():
    root = Path(__file__).resolve().parents[1]
    saved = json.loads((root / "data/summaries.json").read_text(encoding="utf-8"))
    records = [SummaryRecord.model_validate(item).to_dict() for item in saved]
    for original, record in zip(saved, records):
        assert record["tldr"] == original["tldr"]
        assert record["generation_mode"] == original.get("generation_mode", "unknown")
        assert record["evidence_mode"] == original.get("evidence_mode", "unknown")
        assert all(claim["support_status"] == "unverified" for claim in record["provenance"])
    # Live runs may replace saved records with fully labeled summaries. Exercise
    # a versionless record explicitly instead of depending on production state.
    legacy = {key: value for key, value in saved[0].items() if key not in {"generation_mode", "evidence_mode"}}
    html = generate_digest_html([SummaryRecord.model_validate(legacy).to_dict(), *records], "")
    assert "Summary generation: Unknown" in html
    assert "Evidence available: Unknown" in html
