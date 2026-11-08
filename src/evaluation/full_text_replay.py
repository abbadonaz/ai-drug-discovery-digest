"""Controlled real-paper comparison; no automatic scientific adjudication."""
import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from evidence.full_text import retrieve_full_text
from evidence.pipeline import EvidenceBuilderDependencies, FeaturedPaperEvidenceBuilder
from evidence.pdf_extract import extract_pdf_text
from evidence.pdf_sections import extract_sections, build_paper_context
from evidence.pdf_document import extract_pdf_document
from evidence.scientific_sections import extract_document_abstract
from evidence.selector import build_summary_payload
from evidence.section_selection import features
from evaluation.scientific import run_scientific_evaluation
from summarization import llm
from summarization.scientific_summary import summarize_scientific, NOT_ESTABLISHED
from evaluation.checkpoint import CheckpointChat, replay_lock, write_once


def replay(papers, output, model="mistral:latest", tokens=900, *, chat=None):
    with replay_lock(Path(output)):
        return _replay(papers, output, model, tokens, chat=chat)


def _replay(papers, output, model, tokens, *, chat):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if chat is None:
        from ollama import Client
        chat = Client(host="http://127.0.0.1:11434", timeout=1800).chat
    reports, all_summaries = [], []
    for index, paper in enumerate(papers):
        path = paper.get("pdf_path")
        retrieval = retrieve_full_text(paper, output / "pdf-cache") if not path else {
            "outcome": "cached", "path": path, "source_url": paper.get("pdf_url"),
            "paper_id": paper["url"], "document_id": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "reason": None, "attempts": []}
        path = retrieval["path"]
        if not path:
            reports.append({"paper": paper, "retrieval": retrieval, "comparison": "blocked_no_full_text"})
            continue
        # Use exactly the same source abstract and document for both strategies.
        abstract = paper.get("abstract") or extract_document_abstract(extract_pdf_document(path))
        paper = {**paper, "abstract": abstract}
        deps = EvidenceBuilderDependencies(download_pdf=lambda p: path, extract_pdf_text=extract_pdf_text,
            extract_sections=extract_sections, build_paper_context=build_paper_context,
            rank_sentences=lambda values, top_k: values[:top_k], retrieve_full_text=lambda p: retrieval,
            evidence_validator=lambda p: True)
        runs = {}
        with patch("triage.embeddings.get_embedding_model", return_value=None), patch.object(llm, "ENABLE_SUMMARY_QA", False):
            for strategy in ("legacy", "section_aware"):
                target = output / f"paper-{index+1}-{strategy}.json"
                if target.exists():
                    run = json.loads(target.read_text(encoding="utf-8"))
                    if run["summary"]["url"] != paper["url"] or (
                        run["summary"]["generation_mode"] != "llm" and run.get("status") != "completed_invalid_output"
                    ):
                        raise ValueError(f"Invalid existing result: {target}")
                    if run.get("document_id", retrieval["document_id"]) != retrieval["document_id"]:
                        raise ValueError(f"Source PDF differs from checkpoint: {target}")
                    if run.get("generation_parameters", {"temperature": .2, "num_predict": tokens}) != {"temperature": .2, "num_predict": tokens}:
                        raise ValueError(f"Generation settings differ from checkpoint: {target}")
                    recorded_model = run.get("model_identity") or run["summary"].get("model_identity")
                    if recorded_model is not None and recorded_model != model:
                        raise ValueError(f"Model differs from checkpoint: {target}")
                    runs[strategy] = run
                    all_summaries.append(run["summary"])
                    print(f"Preserved {target.name}", flush=True)
                    continue
                record = FeaturedPaperEvidenceBuilder(deps, strategy=strategy).build_featured_record(paper)
                payload = build_summary_payload(record)
                checkpoint = CheckpointChat(target.with_suffix(""), model, tokens, chat)
                with patch.object(llm, "_ollama_chat", checkpoint):
                    summary = llm.summarize_paper_record(record) if strategy == "legacy" else summarize_scientific(record, chat=checkpoint, num_predict=tokens)
                if checkpoint.failure is not None:
                    raise checkpoint.failure
                evidence = payload["evidence"]
                # Same actual model parameters for both formats; prompt format
                # and evidence selection deliberately differ and are reported.
                run = {"summary": summary, "evidence": evidence, "input_chars": len(payload["summary_input"]),
                       "document_id": retrieval["document_id"], "generation_calls": checkpoint.calls,
                       "generation_seconds": sum(call["elapsed_seconds"] for call in checkpoint.calls),
                       "model_identity": checkpoint.calls[-1]["model"] if checkpoint.calls else None,
                       "generation_parameters": {"temperature": .2, "num_predict": tokens},
                       "input_passage_ids": [p.get("passage_id", p.get("evidence_id")) for p in evidence],
                       "candidate_passages": record.get("passages", []),
                       "status": "completed" if summary["generation_mode"] == "llm" else "completed_invalid_output",
                       "structure_validated": summary["generation_mode"] == "llm",
                       "source_sections": sorted({p["section"] for p in evidence}),
                       "quantitative_passages": sum(features(p["text"])["quantitative_metric"] for p in evidence),
                       "traceable_passages": sum(p.get("page_start") is not None for p in evidence),
                       "selected_passages": len(evidence),
                       "scientific_metrics": {key: "not_assessed_no_human_verified_annotations" for key in (
                           "essential_finding_coverage", "quantitative_accuracy", "methodological_specificity",
                           "unsupported_claims", "limitations_coverage", "summary_completeness")},
                       "sections_with_referenced_text": sum(s["text"] != NOT_ESTABLISHED for s in summary.get("scientific_sections", {}).values()) if strategy != "legacy" else None}
                runs[strategy] = run
                write_once(target, run)
                all_summaries.append(summary)
                print(f"Completed paper {index+1} {strategy}: {summary['generation_mode']}", flush=True)
        reports.append({"paper": {k: v for k, v in paper.items() if k not in {"abstract", "pdf_path"}},
                        "document_id": retrieval["document_id"], "retrieval": {k:v for k,v in retrieval.items() if k != "path"},
                        "comparison": "unreviewed_real_paper", "runs": runs})
    if not (output / "summaries.json").exists():
        write_once(output / "summaries.json", all_summaries)
    scientific = run_scientific_evaluation("tests/fixtures/scientific/benchmark.json", output / "summaries.json")
    report = {"model": model, "parameters": {"temperature": .2, "num_predict": tokens},
              "comparison_notes": "Same PDF, source abstract, model and actual generation parameters; prompts necessarily differ. Legacy hashed embeddings use PYTHONHASHSEED=0. No verified annotations.",
              "papers": reports, "scientific_framework": {k: scientific[k] for k in ("benchmark_version", "evaluated_count", "authoritative_benchmark_available")}}
    if not (output / "comparison.json").exists():
        write_once(output / "comparison.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--papers", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="mistral:latest")
    args = parser.parse_args()
    replay(json.loads(Path(args.papers).read_text(encoding="utf-8")), args.output, args.model)


if __name__ == "__main__":
    main()
