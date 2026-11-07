"""Offline legacy/section-aware evidence comparison; not a scientific quality score."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

from evidence.pdf_document import extract_pdf_document
from evidence.pdf_extract import extract_pdf_text
from evidence.pdf_sections import extract_sections
from evidence.scientific_sections import abstract_passages, build_passages, detect_sections
from evidence.section_selection import build_section_payload, family, features
from evidence.selector import build_summary_payload
from evaluation.scientific import evaluate_case
from evaluation.scientific_schema import Benchmark


def compare(papers, benchmark_path=None):
    benchmark = Benchmark.model_validate_json(Path(benchmark_path).read_text(encoding="utf-8")) if benchmark_path else None
    cases = {case.id: case for case in benchmark.cases} if benchmark else {}
    output = []
    # Legacy semantic ranking uses the existing deterministic offline fallback.
    # Run with PYTHONHASHSEED=0; no downloads or inference are needed.
    with patch("triage.embeddings.get_embedding_model", return_value=None):
        for paper in papers:
            document = extract_pdf_document(paper["pdf_path"])
            sections = detect_sections(document) if document["status"] == "success" else []
            passages = build_passages(document, paper["url"]) if sections else []
            passages += abstract_passages(paper)
            legacy_sections = extract_sections(extract_pdf_text(paper["pdf_path"]))
            if paper.get("abstract"):
                legacy_sections["abstract"] = paper["abstract"]
            runs = {}
            for strategy in ("legacy", "section_aware"):
                record = {**paper, "sections": legacy_sections, "passages": passages, "evidence_strategy": strategy}
                payload = build_summary_payload(record) if strategy == "legacy" else build_section_payload(record)
                selected = payload["evidence"]
                counts = Counter(family(item["section"]) for item in selected)
                mode = "pdf_full_text" if any(item.get("source_type") == "pdf" and item["section"] != "abstract" for item in selected) else "abstract_only" if selected and all(item["section"] == "abstract" for item in selected) else "unknown"
                case = cases.get(paper.get("case_id"))
                coverage = evaluate_case(case, {"tldr": " ".join(item["text"] for item in selected)})["automated"]["coverage_proxy"] if case else None
                runs[strategy] = {
                    "selected_count": len(selected), "selected_categories": dict(counts),
                    "category_proportions": {key: counts[key] / len(selected) if selected else None for key in ("abstract", "methods", "results", "discussion", "limitations")},
                    "quantitative_passages": sum(features(item["text"])["quantitative_metric"] for item in selected),
                    "selected_text_chars": sum(len(item["text"]) for item in selected),
                    "prompt_input_chars": len(payload["summary_input"]),
                    "selection_failed": not bool(selected), "selected_evidence_mode": mode,
                    "selection_diagnostics": payload.get("selection_diagnostics"),
                    "evidence": selected, "annotation_coverage_proxy": coverage,
                    "annotation_cohort": case.cohort if case else None,
                }
            output.append({"paper_id": paper["url"], "fixture_kind": paper.get("fixture_kind", "unreviewed"),
                           "pdf_sha256": hashlib.sha256(Path(paper["pdf_path"]).read_bytes()).hexdigest() if Path(paper["pdf_path"]).is_file() else None,
                           "extracted_pages": len(document["pages"]), "detected_sections": len(sections),
                           "candidate_passages": len(passages), "extraction_status": document["status"],
                           "extraction_limitations": document["limitations"], "strategies": runs})
    matched_verified = any(p["strategies"]["section_aware"]["annotation_cohort"] == "verified" for p in output)
    return {"version": "1.0", "scientific_comparison": "review_coverage_proxies_only" if matched_verified else "pending_human_verified_cases",
            "pythonhashseed": os.getenv("PYTHONHASHSEED", "unspecified"),
            "legacy_embedding_backend": "hashed_fallback", "papers": output,
            "extraction_failures": sum(item["extraction_status"] != "success" for item in output),
            "selection_failures": {strategy: sum(p["strategies"][strategy]["selection_failed"] for p in output) for strategy in ("legacy", "section_aware")},
            "evidence_mode_counts": {strategy: dict(Counter(p["strategies"][strategy]["selected_evidence_mode"] for p in output)) for strategy in ("legacy", "section_aware")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--papers", required=True, help="JSON array with title/url/abstract/pdf_path, optional case_id")
    parser.add_argument("--benchmark")
    args = parser.parse_args()
    print(json.dumps(compare(json.loads(Path(args.papers).read_text(encoding="utf-8")), args.benchmark), indent=2))


if __name__ == "__main__":
    main()
