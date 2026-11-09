"""Observed scientific errors; deterministic guards are not entailment tests."""
import hashlib
import json
from pathlib import Path

import pytest

from evidence.pdf_document import prepare_document
from evidence.scientific_sections import build_passages
from evidence.section_selection import build_section_payload
from summarization.scientific_summary import (
    NOT_ESTABLISHED,
    SECTIONS,
    summarize_scientific,
    validate_sections,
)


FIXTURE = Path(__file__).parent / "fixtures/scientific/quality_failures.json"
PAPERS = json.loads(FIXTURE.read_text(encoding="utf-8"))["papers"]
ARCHIVE = FIXTURE.parent / "quality-2026-11-08"


def passage(paper: str, prefix: str) -> dict:
    return next(p for p in PAPERS[paper]["passages"] if p["text"].startswith(prefix))


def check(text: str, source: str, section: str = "validation") -> tuple[dict, list]:
    response = {key: {"text": NOT_ESTABLISHED, "passage_ids": []} for key in SECTIONS}
    response[section] = {"text": text, "passage_ids": ["P1"]}
    return validate_sections(json.dumps(response), [{"passage_id": "P1", "text": source}])


def test_kolta_primary_negative_result_precedes_ablation():
    paper = {"title": "KolTa", "url": PAPERS["2"]["url"],
             "passages": PAPERS["2"]["passages"]}
    evidence = build_section_payload(paper)["evidence"]
    assert evidence[0]["text"].startswith("KolTa ranks first")
    assert "not statistically significant" in evidence[0]["text"]
    assert any(p["text"].startswith("Query efficiency") for p in evidence)


def test_cagenmol_protocol_and_dataset_precede_favorable_filler():
    paper = {"title": "CAGenMol", "url": PAPERS["3"]["url"],
             "passages": PAPERS["3"]["passages"]}
    payload = build_section_payload(paper)
    text = payload["summary_input"]
    assert "CrossDocked2020" in text
    assert "100 molecules generated for each pocket" in text
    assert "EFO is excluded in this benchmark" in text
    assert "Unified Constraint Adaptor" in text
    assert "Results in Table 5" not in text
    assert "Figure 2: Histograms" not in text
    assert payload["selection_diagnostics"]["excluded"]["caption_only"] >= 1
    assert len(text) <= 3600


@pytest.mark.parametrize("paper,prefix,ending", [
    ("1", "As detailed", "Third, we have"),
    ("1", "Across the benchmarks", "These results suggest"),
    ("1", "We investigate", "Across two representative"),
])
def test_dangling_pdf_tail_is_omitted_with_exact_offsets(paper, prefix, ending):
    text = passage(paper, prefix)["text"]
    doc = prepare_document([{
        "page": 1, "width": 600, "height": 800,
        "blocks": [{"bbox": [50, 150, 550, 600], "raw_text": text}],
    }])
    candidates = build_passages(doc, PAPERS[paper]["url"])
    assert candidates
    assert all(ending not in p["text"] for p in candidates)
    assert any("incomplete_block_tail_omitted" in p["limitations"] for p in candidates)
    assert ending in doc["text"]
    for p in candidates:
        assert doc["text"][p["start"]:p["end"]] == p["source_text"]


def test_incomplete_metrics_block_keeps_sample_count_not_just_run_in_label():
    text = passage("3", "Evaluation Metrics")["text"]
    doc = prepare_document([{
        "page": 7, "width": 600, "height": 800,
        "blocks": [{"bbox": [50, 150, 550, 600], "raw_text": text}],
    }])
    candidates = build_passages(doc, PAPERS["3"]["url"])
    assert "100 molecules" in candidates[0]["text"]
    assert "incomplete_sentence" in candidates[0]["limitations"]


def test_supported_non_significant_result_is_not_withheld():
    source = passage("2", "KolTa ranks first")["text"]
    text = "Against GP-Greedy, the difference is not statistically significant."
    sections, issues = check(text, source)
    assert sections["validation"]["text"] == text
    assert not issues


def test_positive_significance_cannot_replace_negative_result():
    source = "Against GP-Greedy, the difference is not statistically significant."
    sections, issues = check("The difference is statistically significant.", source)
    assert sections["validation"]["text"] == NOT_ESTABLISHED
    assert any(i["reason"] == "contradicted_statistical_significance" for i in issues)


def test_significance_stays_scoped_when_source_has_positive_and_negative_comparisons():
    source = passage("2", "KolTa ranks first")["text"]
    correct = "Paired gains against seven comparator strategies were statistically significant."
    sections, issues = check(correct, source)
    assert sections["validation"]["text"] == correct
    assert not issues
    wrong = "The gain against GP-Greedy was statistically significant."
    sections, issues = check(wrong, source)
    assert sections["validation"]["text"] == NOT_ESTABLISHED
    assert any(i["reason"] == "contradicted_statistical_significance" for i in issues)


def test_kolta_decision_rule_is_not_an_observed_result():
    source = passage("2", "We report support")["text"]
    wrong = PAPERS["2"]["observed_claims"]["validation"]
    sections, issues = check(wrong, source)
    assert sections["validation"]["text"] == NOT_ESTABLISHED
    assert any(i["reason"] == "decision_threshold_presented_as_result" for i in issues)
    correct = "Support is reported when both Holm-adjusted tests yield p < 0.05."
    sections, issues = check(correct, source)
    assert sections["validation"]["text"] == correct
    assert not issues


def test_kolta_universal_superiority_is_not_supported_by_paired_wins():
    source = passage("2", "KolTa ranks first")["text"]
    wrong = PAPERS["2"]["observed_claims"]["quantitative_findings"]
    sections, issues = check(wrong, source, "quantitative_findings")
    assert sections["quantitative_findings"]["text"] == NOT_ESTABLISHED
    assert any(i["reason"] == "unsupported_universal_comparison" for i in issues)
    correct = "KolTa won 75 of 78 paired comparisons against seven comparator strategies."
    sections, issues = check(correct, source, "quantitative_findings")
    assert sections["quantitative_findings"]["text"] == correct
    assert not issues


def test_observed_values_are_preserved_but_changed_sign_or_unit_is_rejected():
    source = passage("2", "Query efficiency")["text"]
    correct = "On Drug, 80% macro active recall required 348 queries, saving 76 (18%)."
    sections, issues = check(correct, source, "quantitative_findings")
    assert sections["quantitative_findings"]["text"] == correct
    assert not issues
    for wrong in (correct.replace("348", "-348"), correct.replace("18%", "18 nM")):
        sections, issues = check(wrong, source, "quantitative_findings")
        assert sections["quantitative_findings"]["text"] == NOT_ESTABLISHED
        assert issues


def test_programming_error_in_validation_is_not_hidden_as_inference_failure(monkeypatch):
    def broken(*args):
        raise RuntimeError("validator defect")

    monkeypatch.setattr("summarization.scientific_summary.validate_sections", broken)
    paper = {"title": "CAGenMol", "url": PAPERS["3"]["url"],
             "evidence_strategy": "section_aware", "passages": PAPERS["3"]["passages"]}
    with pytest.raises(RuntimeError, match="validator defect"):
        summarize_scientific(paper, chat=lambda *args, **kwargs: "{}")


@pytest.mark.parametrize("paper,expected", [
    ("2", "evaluation_metric_as_acquisition_rule"),
    ("3", "unreferenced_or_new_number"),
])
def test_compact_missing_reference_field_preserves_other_sections(paper, expected):
    observed = PAPERS[paper]["compact_observed_entries"]
    entries = {key: {"text": NOT_ESTABLISHED, "passage_ids": []} for key in SECTIONS}
    entries.update(observed)
    if paper == "2":
        source = passage(paper, "KolTa ranks first")
        text = "KolTa won 75 of 78 paired comparisons against seven strategies."
    else:
        source = passage(paper, "Results. Table 1")
        text = "CAGenMol reports a 69.7% success rate."
    entries["quantitative_findings"] = {"text": text, "passage_ids": [source["passage_id"]]}
    sections, issues = validate_sections(json.dumps(entries), PAPERS[paper]["passages"])
    assert sections["quantitative_findings"]["text"] == text
    assert sections["relevance"] == {"text": NOT_ESTABLISHED, "passage_ids": []}
    assert {"section": "relevance", "reason": "invalid_section_shape"} in issues
    assert sections["methodology"]["text"] == NOT_ESTABLISHED
    assert {"section": "methodology", "reason": expected} in issues


def test_supported_method_is_not_confused_with_evaluation_metric():
    source = passage("2", "Out-of-fold errors")["text"]
    text = "Out-of-fold predictions use five formulation-grouped folds."
    sections, issues = check(text, source, "methodology")
    assert sections["methodology"]["text"] == text
    assert not issues


@pytest.mark.parametrize("raw", ["{", "[]", '{"research_question": {}}'])
def test_malformed_json_and_top_level_contract_remain_strict(raw):
    with pytest.raises(ValueError):
        validate_sections(raw, PAPERS["2"]["passages"])


def test_evaluation_archive_integrity_and_attempt_history():
    manifest = json.loads((ARCHIVE / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["files"]) == {
        path.name for path in ARCHIVE.iterdir() if path.name != "manifest.json"
    }
    for name, expected in manifest["files"].items():
        text = (ARCHIVE / name).read_text(encoding="utf-8")
        assert hashlib.sha256(text.encode()).hexdigest() == expected

    bundle = json.loads((ARCHIVE / "cached-cases.json").read_text(encoding="utf-8"))
    attempts = bundle["attempts"]
    checkpoints = [item["checkpoint"] for item in attempts.values() if item["checkpoint"]]
    assert len(attempts) == 11
    assert len(checkpoints) == 10
    assert attempts["baseline/paper-2-legacy"]["checkpoint"] is None
    for checkpoint in checkpoints:
        prompt_hash = hashlib.sha256(checkpoint["prompt"].encode()).hexdigest()
        assert prompt_hash == checkpoint["prompt_sha256"]
    truncated = [
        item for item in checkpoints if item["ollama_metadata"]["eval_count"] == 900
    ]
    assert len(truncated) == 2
    for checkpoint in truncated:
        with pytest.raises(json.JSONDecodeError):
            json.loads(checkpoint["response"])


@pytest.mark.parametrize("paper", ["1", "2", "3"])
def test_evaluation_archive_reproduces_final_cached_validation(paper):
    bundle = json.loads((ARCHIVE / "cached-cases.json").read_text(encoding="utf-8"))
    final = bundle["final_revalidations"][paper]
    attempt = bundle["attempts"][final["source_attempt"]]
    evidence = [bundle["passages"][key] for key in attempt["evidence_keys"]]
    sections, issues = validate_sections(attempt["checkpoint"]["response"], evidence)
    assert final["generation_calls"] == 0
    assert sections == final["summary"]["scientific_sections"]
    assert issues == final["summary"]["generation_issues"]
    populated = sum(section["text"] != NOT_ESTABLISHED for section in sections.values())
    assert populated == final["accepted_generated_sections"]
