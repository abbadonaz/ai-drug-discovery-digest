"""Regressions from cached KolTa/CAGenMol failures; no inference or network."""
import json
from pathlib import Path

import pytest
from types import SimpleNamespace

from evidence.pdf_document import prepare_document
from evidence.pdf_sections import extract_sections
from evidence.pipeline import FeaturedPaperEvidenceBuilder
from evidence.scientific_sections import build_passages, extract_document_abstract
from evidence.section_selection import SelectionSettings, build_section_payload
from summarization.ollama_client import ChatText
from summarization.scientific_summary import NOT_ESTABLISHED, SECTIONS, summarize_scientific, validate_sections
from web.digest import _render_summary_modes


OBSERVED = json.loads((Path(__file__).parent / "fixtures/stabilization/observed_failures.json").read_text(encoding="utf-8"))["papers"]


def document(text):
    return prepare_document([{"page": 1, "width": 600, "height": 800,
                              "blocks": [{"bbox": [60, 200, 280, 600], "raw_text": text}]}])


def response(section, text, ids):
    entries = {key: {"text": NOT_ESTABLISHED, "passage_ids": []} for key in SECTIONS}
    entries[section] = {"text": text, "passage_ids": ids}
    return json.dumps(entries)


@pytest.mark.parametrize("name", ["kolta", "cagenmol"])
def test_observed_sparse_font_markers_do_not_reject_readable_prose(name):
    observed = OBSERVED[name]
    page = observed["abstract_page"]
    doc = prepare_document([{**page, "blocks": [*page["blocks"], {
        "bbox": [60, 100, 280, 190], "raw_text": observed["font_marker_block"]}]}])
    assert doc["status"] == "success"
    assert "unmapped_font_glyphs" in doc["limitations"]
    assert doc["quality_diagnostics"]["unmapped_glyph_count"] > 0
    assert "(cid:" in doc["raw_text"]
    payload = build_section_payload({"title": name, "url": observed["url"],
                                     "passages": build_passages(doc, observed["url"])})
    assert all("(cid:" not in p["text"] for p in payload["evidence"])


def test_glyph_dominated_or_scanned_text_is_still_rejected():
    assert document("(cid:88) " * 200)["status"] == "low_quality"
    assert document("123 ??")["status"] == "low_quality"


def test_complete_cagenmol_abstract_survives_body_methods_and_column_order():
    doc = prepare_document([OBSERVED["cagenmol"]["abstract_page"]])
    abstract = extract_document_abstract(doc)
    assert "methods often optimize" in abstract
    assert "github.com/Lee612-1/CAGenMol." in abstract
    assert "The discovery of novel" not in abstract
    sections = extract_sections("Abstract " + abstract + " Introduction This introduces the study. Results These are results.")
    assert "github.com/Lee612-1/CAGenMol." in sections["abstract"]
    assert "This introduces" not in sections["abstract"]


def test_kolta_inline_abstract_stops_before_impact_statement():
    abstract = extract_document_abstract(prepare_document([OBSERVED["kolta"]["abstract_page"]]))
    assert "348 additional formulation queries" in abstract
    assert abstract.endswith("component roles and physical constraints.")
    assert "Impact Statement" not in abstract


def test_full_available_abstract_is_kept_when_context_is_budgeted():
    doc = prepare_document([OBSERVED["cagenmol"]["abstract_page"]])
    dependencies = SimpleNamespace(
        retrieve_full_text=lambda paper: {"path": "cached.pdf", "outcome": "cached"},
        extract_pdf_document=lambda path: doc, evidence_validator=lambda record: True)
    record = FeaturedPaperEvidenceBuilder(dependencies, strategy="section_aware").build_featured_record({
        "title": "CAGenMol", "url": OBSERVED["cagenmol"]["url"], "evidence_char_budget": 600})
    assert len(record["abstract"]) > 600
    assert record["abstract"].endswith("github.com/Lee612-1/CAGenMol.")
    assert len(record["context"]) <= 600
    assert record["selection_diagnostics"]["available_abstract_chars"] == len(record["abstract"])


def test_abstract_continuation_is_preserved_until_next_page_heading():
    pages = [
        {"page": 1, "width": 600, "height": 800, "blocks": [
            {"bbox": [60, 550, 280, 600], "raw_text": "Abstract"},
            {"bbox": [60, 100, 280, 540], "raw_text": "Molecular prediction continues onto the next page with an incomplete"}]},
        {"page": 2, "width": 600, "height": 800, "blocks": [
            {"bbox": [60, 650, 280, 700], "raw_text": "sentence and the final available abstract result."},
            {"bbox": [60, 600, 140, 630], "raw_text": "Introduction"},
            {"bbox": [60, 200, 280, 590], "raw_text": "Body text must not enter the abstract."}]},
    ]
    abstract = extract_document_abstract(prepare_document(pages))
    assert abstract.endswith("final available abstract result.")
    assert "Body text" not in abstract


def test_results_and_author_limitations_fit_before_long_methods():
    text = ("Methods\n" + "The molecular model uses a training dataset and calibrated acquisition. " * 35
            + "\nResults\nResults. KolTa reaches 80% recall in 348 queries, saving 18% against the comparator.\n"
            + "Limitations. Temperature extrapolation has not been evaluated. Only temperature varies.\n")
    doc = document(text)
    passages = build_passages(doc, "test", max_chars=300)
    for passage in passages:
        assert doc["text"][passage["start"]:passage["end"]] == passage["source_text"]
    payload = build_section_payload({"title": "KolTa pattern", "url": "test", "passages": passages},
                                    SelectionSettings(char_budget=800, max_passages=3))
    assert "348 queries" in payload["summary_input"]
    assert "extrapolation has not been evaluated" in payload["summary_input"]
    assert len(payload["summary_input"]) <= 800


def test_author_caveat_is_preferred_to_result_prose_under_limitations_heading():
    paper = {"title": "CAGenMol pattern", "url": "test", "passages": [
        {"passage_id": "wrong", "section": "limitations", "text": "Results. Success rate reaches 69.7% and outperforms the baseline on the benchmark."},
        {"passage_id": "caveat", "section": "limitations", "text": "Several limitations remain: prediction errors are not accounted for and compute is limited."},
    ]}
    payload = build_section_payload(paper, SelectionSettings(char_budget=300, max_passages=1))
    assert payload["evidence"][0]["passage_id"] == "caveat"


def test_numerical_outcome_precedes_high_scoring_benchmark_description():
    paper = {"title": "Observed ranking failure pattern", "url": "test", "passages": [
        {"passage_id": "description", "section": "results", "text": "The molecular benchmark evaluates 58 tasks with scaffold train-test splits and random seeds, comparing win rates and baseline scores."},
        {"passage_id": "outcome", "section": "results", "text": "The model achieves a 69.7% success rate compared with the baseline."},
    ]}
    payload = build_section_payload(paper, SelectionSettings(char_budget=300, max_passages=1))
    assert payload["evidence"][0]["passage_id"] == "outcome"


def test_invalid_kolta_reference_is_withheld_without_discarding_other_sections():
    observed = OBSERVED["kolta"]
    sections, issues = validate_sections(observed["raw_response"], observed["original_evidence"])
    assert sections["relevance"]["text"] == NOT_ESTABLISHED
    assert sections["methodology"]["text"] != NOT_ESTABLISHED
    assert {"section": "relevance", "reason": "unknown_passage_reference"} in issues
    assert sections["validation"]["text"] == NOT_ESTABLISHED


def test_cagenmol_validation_is_not_supported_by_problem_statement():
    observed = OBSERVED["cagenmol"]
    sections, issues = validate_sections(observed["raw_response"], observed["original_evidence"])
    assert sections["validation"]["text"] == NOT_ESTABLISHED
    assert {"section": "validation", "reason": "validation_without_protocol_evidence"} in issues


@pytest.mark.parametrize("claim,source", [
    ("The measured affinity was 10 nM.", "The measured affinity was 10 uM."),
    ("The docking score was -8.18 kcal/mol.", "The docking score was 8.18 kcal/mol."),
    ("Success rate was 90%.", "Success rate was 69.7%."),
    ("External validation confirmed the model.", "No external validation was performed."),
    ("Prospective validation confirmed the model.", "The retrospective benchmark evaluated the model."),
    ("The improvement was statistically significant.", "The difference was not statistically significant."),
    ("The article does not discuss limitations.", "The framework addresses molecular generation constraints."),
])
def test_conservative_numeric_and_validation_checks(claim, source):
    evidence = [{"passage_id": "P1", "text": source}]
    sections, issues = validate_sections(response("validation", claim, ["P1"]), evidence)
    assert sections["validation"]["text"] == NOT_ESTABLISHED
    assert issues


def test_supported_units_and_unicode_minus_are_preserved():
    evidence = [{"passage_id": "P1", "text": "Evaluation measured a docking score of \u22128.18 kcal/mol and 18% savings."}]
    text = "Evaluation reported -8.18 kcal/mol and 18 percent savings."
    sections, issues = validate_sections(response("validation", text, ["P1"]), evidence)
    assert sections["validation"]["text"] == text
    assert not issues


def test_numeric_range_is_not_misread_as_a_negative_value():
    evidence = [{"passage_id": "P1", "text": "The benchmark reports a speedup of 4.8\u201327.3 times."}]
    text = "The benchmark reports speedups from 4.8 to 27.3 times."
    sections, issues = validate_sections(response("quantitative_findings", text, ["P1"]), evidence)
    assert sections["quantitative_findings"]["text"] == text
    assert not issues


def test_all_invalid_sections_use_labeled_fallback_with_attempt_metadata():
    evidence = [{"passage_id": "P1", "section": "abstract", "source_type": "abstract",
                 "text": "This framework evaluates molecular prediction on a retrospective benchmark dataset."}]
    raw = json.dumps({key: {"text": "Invalid generated analysis.", "passage_ids": ["invented"]} for key in SECTIONS})
    paper = {"title": "Test", "url": "https://example.org/test", "evidence_strategy": "section_aware", "passages": evidence}
    summary = summarize_scientific(paper, chat=lambda *args, **kwargs: ChatText(raw, "mistral:latest", {"num_predict": 900}))
    assert summary["generation_mode"] == "extractive_fallback"
    assert summary.get("model_identity") is None
    assert summary["attempted_model_identity"] == "mistral:latest"
    assert "Source passage (unverified)" in summary["tldr"]
    assert "Sections withheld by mechanical checks: 6" in _render_summary_modes(summary)
    assert all(c["support_status"] == "unverified" for c in summary["provenance"])
