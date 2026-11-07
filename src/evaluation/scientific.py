"""Offline annotation checks. Exact statement agreement is not general entailment."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from evaluation.scientific_schema import Benchmark, HumanAssessment


CATEGORIES = ("finding", "method", "result", "comparison", "limitation")
QUANTITATIVE_ERRORS = {"value", "unit", "metric", "dataset", "direction", "conditions"}
EVALUATOR_VERSION = "1.0"


def fingerprint(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_hash(value):
    return fingerprint(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def normalize(text):
    # Keep numbers, signs, units and negations intact. Only case/space and final
    # sentence punctuation are ignored. Substrings must never imply agreement.
    return re.sub(r"\s+", " ", text).strip().rstrip(".!?").casefold()


def split_claims(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if part.strip()]


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def evaluate_case(case, summary, assessment=None):
    text = summary.get("tldr", "")
    if not isinstance(text, str):
        raise ValueError("Summary tldr must be a string")
    claims = split_claims(text)
    normalized = {normalize(claim) for claim in claims}
    hits = {item.id: bool(normalized & {normalize(s) for s in [item.statement, *item.accepted_statements]})
            for item in case.annotations}
    failures = [item for item in case.must_not_infer if normalize(item.statement) in normalized]
    coverage = {}
    for category in CATEGORIES:
        items = [item for item in case.annotations if item.category == category]
        coverage[category] = ratio(sum(hits[item.id] for item in items), len(items))
    coverage["overall"] = ratio(sum(hits.values()), len(hits))
    quantities = []
    for quantity in case.quantities:
        errors = [item for item in failures if item.annotation_id == quantity.annotation_id
                  and item.error_type in QUANTITATIVE_ERRORS]
        status = "failed" if errors else "reference_match" if hits[quantity.annotation_id] else "not_assessed"
        quantities.append({**quantity.model_dump(), "status": status,
                           "errors": [item.error_type for item in errors]})
    judgments = {}
    if assessment:
        if assessment.case_id != case.id or assessment.summary_sha256 != fingerprint(text):
            raise ValueError("Human assessment is not bound to this case and exact summary")
        for judgment in assessment.claims:
            key = normalize(judgment.claim)
            if key in judgments or key not in normalized:
                raise ValueError("Duplicate or absent assessed claim")
            if not set(judgment.evidence_ids) <= {p.id for p in case.passages}:
                raise ValueError("Human judgment references unknown evidence")
            if judgment.status in {"supported", "contradicted"} and not judgment.evidence_ids:
                raise ValueError("Support/contradiction judgments require evidence references")
            judgments[key] = judgment
    claim_results = []
    for claim in claims:
        judgment = judgments.get(normalize(claim))
        # Positional provenance and incoming support_status are never consulted.
        claim_results.append({"claim": claim,
                              "status": judgment.status if judgment else "not_assessed",
                              "method": "human_review" if judgment else "none",
                              "evidence_ids": judgment.evidence_ids if judgment else [],
                              "rationale": judgment.rationale if judgment else "Requires evidence review; lexical agreement is not entailment"})
    known = {normalize(s) for a in case.annotations for s in [a.statement, *a.accepted_statements]}
    known |= {normalize(item.statement) for item in case.must_not_infer}
    missing = [item.id for item in case.annotations if not hits[item.id]]
    return {
        "case_id": case.id, "cohort": case.cohort, "review": case.review.model_dump(),
        "evaluated": True, "summary_sha256": fingerprint(text),
        "generation_mode": summary.get("generation_mode", "unknown"),
        "evidence_mode": summary.get("evidence_mode", "unknown"),
        "reference_evidence_scope": case.evidence_scope,
        "automated": {
            "method": "exact_annotated_statement_checks", "coverage_proxy": coverage,
            "unmatched_annotation_ids": missing,
            "quantitative_checks": quantities,
            "negative_controls": {"status": "failed" if failures else "no_known_violation",
                                  "failures": [item.model_dump() for item in failures]},
            "unassessed_claims": [claim for claim in claims if normalize(claim) not in known],
        },
        "evidence_support": claim_results,
        "human_assessment": assessment.model_dump() if assessment else None,
        "missing_or_unassessable": (["reference_annotations"] if not case.annotations else [])
        + (["quantitative_annotations"] if not case.quantities else [])
        + (["summary_text"] if not text.strip() else [])
        + (["human_review"] if not assessment else [])
        + (["generation_mode"] if not summary.get("generation_mode") else [])
        + (["evidence_mode"] if not summary.get("evidence_mode") else []),
    }


def aggregate(results):
    evaluated = [item for item in results if item["evaluated"]]
    coverage = {}
    for category in (*CATEGORIES, "overall"):
        values = [item["automated"]["coverage_proxy"][category] for item in evaluated]
        coverage[category] = ratio(sum(v["numerator"] for v in values), sum(v["denominator"] for v in values))
    quantities = Counter(q["status"] for item in evaluated for q in item["automated"]["quantitative_checks"])
    support = Counter(c["status"] for item in evaluated for c in item["evidence_support"])
    return {
        "case_count": len(results), "evaluated_count": len(evaluated),
        "coverage_proxy": coverage,
        "quantitative_reference_agreement": ratio(quantities["reference_match"], quantities["reference_match"] + quantities["failed"]),
        "quantitative_counts": {status: quantities[status] for status in ("reference_match", "failed", "not_assessed")},
        "cases_with_known_errors": sum(item["automated"]["negative_controls"]["status"] == "failed" for item in evaluated),
        "evidence_support_counts": {status: support[status] for status in ("supported", "contradicted", "insufficient_evidence", "not_assessed")},
        "human_supported_fraction": ratio(support["supported"], sum(support.values()) - support["not_assessed"]),
    }


def run_scientific_evaluation(benchmark_path, summaries_path, *, assessments_path=None, timestamp=None):
    benchmark_data = json.loads(Path(benchmark_path).read_text(encoding="utf-8"))
    benchmark = Benchmark.model_validate(benchmark_data)
    summaries = json.loads(Path(summaries_path).read_text(encoding="utf-8"))
    if not isinstance(summaries, list) or any(not isinstance(item, dict) for item in summaries):
        raise ValueError("Expected a summaries.json array")
    assessment_data = json.loads(Path(assessments_path).read_text(encoding="utf-8")) if assessments_path else []
    assessments = [HumanAssessment.model_validate(item) for item in assessment_data]
    if any(item.benchmark_sha256 != canonical_hash(benchmark_data) for item in assessments):
        raise ValueError("Human assessment refers to a different benchmark revision")
    if len({item.case_id for item in assessments}) != len(assessments):
        raise ValueError("Duplicate assessments")
    review_by_id = {item.case_id: item for item in assessments}
    if not review_by_id.keys() <= {case.id for case in benchmark.cases}:
        raise ValueError("Assessment for an unknown case")
    results, used = [], set()
    for case in benchmark.cases:
        # Explicit IDs take precedence. Exact URL is the legacy pipeline adapter;
        # never fuzzy-match titles or silently choose one of duplicate outputs.
        matches = [(i, item) for i, item in enumerate(summaries)
                   if item.get("case_id") == case.id or (not item.get("case_id") and case.url and item.get("url") == case.url)]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous summaries for {case.id}")
        if not matches:
            if case.id in review_by_id:
                raise ValueError("Assessment has no matching summary")
            results.append({"case_id": case.id, "cohort": case.cohort, "evaluated": False,
                            "missing_or_unassessable": ["summary"]})
            continue
        index, summary = matches[0]
        if index in used:
            raise ValueError("A summary matches multiple benchmark cases")
        used.add(index)
        results.append(evaluate_case(case, summary, review_by_id.get(case.id)))
    groups = {name: aggregate([item for item in results if item["cohort"] == name])
              for name in ("verified", "synthetic", "unreviewed")}
    return {
        "schema_version": benchmark.schema_version, "benchmark_version": benchmark.benchmark_version,
        "evaluator_version": EVALUATOR_VERSION,
        "evaluation_timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "benchmark_sha256": canonical_hash(benchmark_data), "summaries_sha256": canonical_hash(summaries),
        "assessments_sha256": canonical_hash(assessment_data),
        "case_count": len(results), "evaluated_count": len(used),
        "unmatched_summary_count": len(summaries) - len(used),
        "cohorts": groups, "cases": results,
        "authoritative_benchmark_available": bool(groups["verified"]["evaluated_count"]),
        "limitations": "Coverage and quantity agreement are exact-statement proxies, not factuality scores. Only human-reviewed real cases enter the verified cohort. No overall quality score.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--summaries", required=True)
    parser.add_argument("--assessments")
    parser.add_argument("--timestamp", help="Fixed report timestamp for reproducible fixture runs")
    args = parser.parse_args()
    report = run_scientific_evaluation(args.benchmark, args.summaries,
                                       assessments_path=args.assessments, timestamp=args.timestamp)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
