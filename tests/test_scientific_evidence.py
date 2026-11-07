import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from evidence.pdf_document import extract_pdf_document, normalize_block, prepare_document
from evidence.scientific_sections import abstract_passages, build_passages, detect_sections, heading
from evidence.section_selection import SelectionSettings, build_section_payload, family, select_passages
from evidence.selector import build_summary_payload
from evidence.pipeline import EvidenceBuilderDependencies, FeaturedPaperEvidenceBuilder, EvidencePreparationPipeline
from evidence.pdf_extract import extract_pdf_text
from evidence.pdf_sections import extract_sections, build_paper_context
from evaluation.evidence_comparison import compare
from summarization import llm


ROOT = Path(__file__).resolve().parent / "fixtures" / "evidence"
PDF = ROOT / "scientific-study.pdf"
ABSTRACT = ("This synthetic study presents molecular prediction for drug discovery using graph models. "
            "The framework combines molecular descriptors with a learning approach for compound prioritization. "
            "The study evaluates prediction performance on a fictional benchmark for molecular screening.")
PAPER = {"title": "Synthetic molecular prediction", "url": "https://example.org/toy", "abstract": ABSTRACT}


def record():
    document = extract_pdf_document(PDF)
    return {**PAPER, "evidence_strategy": "section_aware", "evidence_mode": "pdf_full_text",
            "passages": build_passages(document, PAPER["url"]), "document": document}


def test_pages_offsets_headers_and_two_columns():
    document = extract_pdf_document(PDF)
    assert document["status"] == "success"
    assert len(document["pages"]) == 3
    assert document["pages"][1]["layout"] == "two_column_heuristic"
    assert "SYNTHETIC FIXTURE" not in document["text"]
    assert "SYNTHETIC FIXTURE" in document["raw_text"]
    passages = build_passages(document, PAPER["url"])
    assert {p["page_start"] for p in passages} == {1, 2, 3}
    for passage in passages:
        assert document["text"][passage["start"]:passage["end"]] == passage["source_text"]
    methods = next(p for p in passages if "1000 compounds" in p["text"])
    result = next(p for p in passages if "Removing graph" in p["text"])
    assert methods["section"] == "training_validation"
    assert result["section"] == "results"
    assert "1.2 to 1.0 log mol/L" in document["text"].replace("\n", " ")


@pytest.mark.parametrize("text,category", [
    ("2 Materials and Methods", "methods"), ("3.1 Training and Validation", "training_validation"),
    ("Experimental Setup", "experimental_setup"), ("Datasets", "datasets"),
    ("Model Architecture", "model_architecture"), ("Results and Discussion", "results_discussion"),
    ("Background", "introduction"), ("Conclusions", "conclusion"),
    ("Supplementary Information", "supplementary"), ("References", "references"),
    ("These results suggest an improvement in prediction.", None),
    ("Methods were compared on the dataset.", None), ("2.1 mg/L was measured.", None),
])
def test_heading_taxonomy_and_false_positives(text, category):
    assert heading(text) == category


def test_multiline_and_nested_headings():
    sections = detect_sections(extract_pdf_document(PDF))
    assert any(s["title"] == "2 Materials and Methods" for s in sections)
    nested = next(s for s in sections if s["title"] == "3.1 Ablation Analysis")
    assert nested["category"] == "results"
    assert nested["detection"] == "inherited_numbered_subsection"
    assert nested["page_start"] == nested["page_end"] == 2


def test_normalization_preserves_scientific_symbols_and_ambiguous_hyphens():
    text = normalize_block("molec-\nular predic-\ntion\nRMSE = 1.0 ± 0.2 μM; ΔG = −8 kcal/mol [12].\nprotein-\nligand\n1.2-\n1.4")
    assert "molecular prediction" in text
    assert "1.0 ± 0.2 μM; ΔG = −8 kcal/mol [12]" in text
    assert "protein-ligand" in text
    assert "1.2-\n1.4" in text


def test_selection_covers_methods_results_limitations_and_excludes_references():
    payload = build_summary_payload(record())
    sections = {family(p["section"]) for p in payload["evidence"]}
    assert {"methods", "results", "limitations"} <= sections
    assert "references" not in sections
    assert "Scaffold training and test" in payload["summary_input"]
    assert "1.2 to 1.0 log mol/L" in payload["summary_input"]
    assert "No external validation" in payload["summary_input"]
    assert all(p["selection_reasons"] and p["support_status"] == "unverified" for p in payload["evidence"])
    assert any(p.get("table_id") == "Table 1" for p in payload["evidence"])
    assert payload["selection_diagnostics"]["excluded"]["numeric_block"] == 1


def test_deterministic_ids_deduplication_and_budget():
    paper = record()
    assert paper["passages"] == record()["passages"]
    duplicate = {**paper["passages"][0], "passage_id": "duplicate"}
    paper["passages"].append(duplicate)
    selected, diagnostics = select_passages(paper, SelectionSettings(char_budget=1500, max_passages=20))
    assert len({p["text"] for p in selected}) == len(selected)
    assert diagnostics["excluded"]["duplicate"] >= 1
    assert diagnostics["input_chars"] <= 1500
    empty = build_section_payload(paper, SelectionSettings(char_budget=1))
    assert not empty["evidence"]
    assert empty["selection_diagnostics"]["excluded"]["budget"] > 0
    assert empty["selection_diagnostics"]["missing_coverage"]


def dependencies(path=PDF):
    return EvidenceBuilderDependencies(download_pdf=lambda paper: path, extract_pdf_text=extract_pdf_text,
                                       extract_sections=extract_sections, build_paper_context=build_paper_context,
                                       rank_sentences=lambda sentences, top_k: sentences[:top_k])


@pytest.mark.parametrize("kind", ["missing", "malformed", "empty"])
def test_failed_and_low_quality_extraction_falls_back(tmp_path, kind):
    path = tmp_path / "bad.pdf"
    if kind != "missing":
        path.write_bytes(b"not a pdf" if kind == "malformed" else b"")
    document = extract_pdf_document(path)
    assert document["status"] == "failed"
    paper = FeaturedPaperEvidenceBuilder(dependencies(path), strategy="section_aware").build_featured_record(PAPER)
    assert paper["evidence_mode"] == "abstract_only"
    assert paper["extraction_diagnostics"]["status"] == "failed"
    assert all(p["page_start"] is None for p in paper["selected_evidence"])
    low = prepare_document([{"page": 1, "width": 600, "height": 800, "blocks": [{"bbox": [40, 500, 200, 600], "raw_text": "123 ??"}]}])
    assert low["status"] == "low_quality"


def test_abstract_only_pdf_and_legacy_default(monkeypatch):
    monkeypatch.setattr("triage.embeddings.get_embedding_model", lambda: None)
    builder = FeaturedPaperEvidenceBuilder(dependencies(ROOT / "abstract-only.pdf"), strategy="section_aware")
    result = builder.build_featured_record(PAPER)
    assert result["evidence_mode"] == "abstract_only"
    selected_texts = [p["text"].casefold() for p in result["selected_evidence"]]
    assert not any(a in b for i, a in enumerate(selected_texts) for j, b in enumerate(selected_texts) if i != j)
    assert FeaturedPaperEvidenceBuilder(dependencies()).strategy == "legacy"
    legacy = build_summary_payload({**PAPER, "evidence_strategy": "legacy", "sections": {"abstract": ABSTRACT}})
    assert all(item["section"] == "abstract" for item in legacy["evidence"])
    assert any(item["section"] != "abstract" for item in build_summary_payload(record())["evidence"])
    monkeypatch.setattr("evidence.selector.EVIDENCE_SELECTION_STRATEGY", "section_aware")
    legacy_record = FeaturedPaperEvidenceBuilder(dependencies(), strategy="legacy").build_featured_record(PAPER)
    assert legacy_record["evidence_strategy"] == "legacy"
    assert all(p["section"] == "abstract" for p in build_summary_payload(legacy_record)["evidence"])


def test_both_llm_attempts_receive_all_selected_evidence_and_metadata(monkeypatch):
    paper = FeaturedPaperEvidenceBuilder(dependencies(), strategy="section_aware").build_featured_record(PAPER)
    payload = build_summary_payload(paper)
    prompts = []
    def chat(prompt, **kwargs):
        prompts.append(prompt)
        return "bad" if len(prompts) == 1 else "This synthetic study used a graph model with scaffold validation. The results report RMSE on a fictional dataset."
    monkeypatch.setattr(llm, "_ollama_chat", chat)
    monkeypatch.setattr(llm, "ENABLE_SUMMARY_QA", False)
    result = llm.summarize_paper_record(paper)
    assert len(prompts) == 2
    for prompt in prompts:
        for item in payload["evidence"]:
            assert item["text"] in prompt
    assert result["generation_mode"] == "llm"
    assert result["selected_evidence"] == payload["evidence"]
    assert all(c["support_status"] == "unverified" for c in result["provenance"])
    assert any(e.get("page_start") == 2 for c in result["provenance"] for e in c["evidence"])


def test_budget_above_legacy_limit_reaches_both_prompts(monkeypatch):
    # Explicitly exercise >2200 chars; don't merely test a short prompt.
    text = "Methods: scaffold split with 1000 molecules. " * 35 + "Results: RMSE 1.0 log mol/L versus 1.2 for baseline. " * 25
    assert 2200 < len(text) < 3600
    prompts = []
    monkeypatch.setattr(llm, "_ollama_chat", lambda prompt, **kwargs: prompts.append(prompt) or "bad")
    llm.summarize_with_llm("Synthetic", text, max_context_chars=3600)
    assert len(prompts) == 2
    assert all(text.strip() in prompt for prompt in prompts)


def test_offline_replay_publication_and_evaluation_compatibility(tmp_path, monkeypatch):
    from digest_core.models import PipelinePaths, PipelineSettings
    from digest_core.publication import verify_manifest
    from pipeline.research_pipeline import ResearchDigestPipeline
    from web.publishing import DigestPublisher
    from evaluation.scientific import run_scientific_evaluation
    def blocked(*args, **kwargs):
        raise RuntimeError("offline")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr("triage.embeddings.get_embedding_model", lambda: None)
    monkeypatch.setattr(llm, "_ollama_chat", blocked)
    monkeypatch.chdir(tmp_path)
    for strategy in ("legacy", "section_aware"):
        directory = tmp_path / strategy
        directory.mkdir()
        monkeypatch.chdir(directory)
        builder = FeaturedPaperEvidenceBuilder(dependencies(), strategy=strategy)
        pipeline = ResearchDigestPipeline(SimpleNamespace(fetch_all=lambda: [PAPER]),
            EvidencePreparationPipeline(builder, 1, 0), DigestPublisher(PipelinePaths()),
            PipelinePaths(), PipelineSettings(enable_cluster_selection=False), llm.summarize_papers,
            relevance_filter=lambda papers: papers, narrative_generator=lambda papers: "Offline synthetic replay.")
        result = pipeline.run()
        assert result.status == "published"
        verify_manifest("docs/publication.json", result.run_id)
        summaries = json.loads(Path("data/summaries.json").read_text())
        assert summaries[0]["generation_mode"] == "extractive_fallback"
        assert all(c["support_status"] == "unverified" for c in summaries[0]["provenance"])
        if strategy == "section_aware":
            assert summaries[0]["selected_evidence"]
        report = run_scientific_evaluation(ROOT.parent / "scientific" / "benchmark.json", "data/summaries.json")
        assert not report["authoritative_benchmark_available"]


def test_comparison_is_offline_and_reproducible(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *args: pytest.fail("network"))
    papers = [{**PAPER, "pdf_path": str(PDF), "fixture_kind": "synthetic"}]
    a = compare(papers)
    assert a == compare(papers)
    assert a["scientific_comparison"] == "pending_human_verified_cases"
    results = a["papers"][0]["strategies"]
    assert results["legacy"]["selected_categories"] == {"abstract": 3}
    assert results["section_aware"]["selected_categories"]["methods"] >= 1
    assert results["section_aware"]["selected_categories"]["results"] >= 1
    assert a["extraction_failures"] == 0
