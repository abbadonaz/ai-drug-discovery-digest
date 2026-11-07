import copy
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from pydantic import ValidationError

from evaluation.scientific import canonical_hash, evaluate_case, fingerprint, run_scientific_evaluation
from evaluation.scientific_schema import Benchmark, Case, HumanAssessment


FIXTURES = Path(__file__).parent / "fixtures" / "scientific"
DATA = json.loads((FIXTURES / "benchmark.json").read_text(encoding="utf-8"))
BENCHMARK = Benchmark.model_validate(DATA)


def run(name="accurate", **kwargs):
    return run_scientific_evaluation(FIXTURES / "benchmark.json",
                                     FIXTURES / f"summaries-{name}.json", timestamp="2026-11-07T00:00:00Z", **kwargs)


def test_accurate_reference_agreement_is_not_factual_verification():
    report = run()
    assert report["case_count"] == report["evaluated_count"] == 7
    assert report["cohorts"]["synthetic"]["coverage_proxy"]["overall"] == {"numerator": 35, "denominator": 35, "value": 1.0}
    assert report["cohorts"]["synthetic"]["quantitative_reference_agreement"]["value"] == 1
    assert report["cohorts"]["synthetic"]["evidence_support_counts"]["not_assessed"] == 35
    assert report["cohorts"]["verified"]["coverage_proxy"]["overall"]["value"] is None
    assert not report["authoritative_benchmark_available"]


@pytest.mark.parametrize("case,control", [(case, control) for case in BENCHMARK.cases for control in case.must_not_infer],
                         ids=[f"{case.id}-{control.id}" for case in BENCHMARK.cases for control in case.must_not_infer])
def test_every_negative_control_fails(case, control):
    result = evaluate_case(case, {"tldr": control.statement})
    check = result["automated"]["negative_controls"]
    assert check["status"] == "failed"
    assert check["failures"][0]["error_type"] == control.error_type
    if control.error_type in {"value", "unit", "metric", "dataset", "direction", "conditions"}:
        assert result["automated"]["quantitative_checks"][0]["status"] == "failed"


@pytest.mark.parametrize("category", ["finding", "method", "result", "comparison", "limitation"])
def test_omissions_lower_category_coverage(category):
    case = BENCHMARK.cases[0]
    text = " ".join(a.statement for a in case.annotations if a.category != category)
    result = evaluate_case(case, {"tldr": text})
    assert result["automated"]["coverage_proxy"][category]["value"] == 0
    assert category in result["automated"]["unmatched_annotation_ids"]


def test_unknown_paraphrase_negation_and_numbers_are_not_approved():
    case = BENCHMARK.cases[0]
    for text in ["It is false that " + case.annotations[2].statement,
                 case.annotations[2].statement.replace("1.0", "0.314159"),
                 "Performance improved on a held-out molecular set."]:
        result = evaluate_case(case, {"tldr": text})
        assert result["automated"]["quantitative_checks"][0]["status"] == "not_assessed"
        assert result["automated"]["unassessed_claims"] == [text]
        assert result["evidence_support"][0]["status"] == "not_assessed"


def test_modes_are_metadata_not_inferred_support():
    case = BENCHMARK.cases[0]
    for mode in ("abstract_only", "pdf_full_text", "unknown"):
        result = evaluate_case(case, {"tldr": case.reference_summary, "evidence_mode": mode,
                                      "provenance": [{"claim": case.reference_summary, "support_status": "supported"}]})
        assert result["evidence_mode"] == mode
        assert all(c["status"] == "not_assessed" for c in result["evidence_support"])
    assert evaluate_case(case, {"tldr": ""})["generation_mode"] == "unknown"


def test_missing_annotations_have_null_denominators():
    data = copy.deepcopy(DATA["cases"][0])
    data.update(annotations=[], quantities=[], must_not_infer=[])
    case = Case.model_validate(data)
    result = evaluate_case(case, {"tldr": "An arbitrary sentence."})
    assert result["automated"]["coverage_proxy"]["overall"]["value"] is None
    assert "reference_annotations" in result["missing_or_unassessable"]


def test_human_assessments_are_explicit_and_bound_to_exact_text():
    case = BENCHMARK.cases[0]
    claim = case.must_not_infer[0].statement
    assessment = HumanAssessment(case_id=case.id, benchmark_sha256=canonical_hash(DATA), summary_sha256=fingerprint(claim), reviewer="test-only reviewer",
                                 reviewed_at="2026-11-07", claims=[dict(claim=claim, status="contradicted",
                                 evidence_ids=["E1"], rationale="Synthetic control conflicts with source value")], rubric={"accuracy": 0})
    result = evaluate_case(case, {"tldr": claim}, assessment)
    assert result["evidence_support"][0]["status"] == "contradicted"
    assert result["human_assessment"]["rubric"] == {"accuracy": 0}
    with pytest.raises(ValueError, match="exact summary"):
        evaluate_case(case, {"tldr": claim + " Changed."}, assessment)


def test_verified_unreviewed_and_synthetic_aggregation_separate(tmp_path):
    # These are test-only mock review records, not benchmark annotations.
    data = copy.deepcopy(DATA)
    for index, status in [(0, "verified"), (1, "unreviewed")]:
        case = data["cases"][index]
        case["kind"] = "real"
        case["review"].update(status=status, reviewer="TEST ONLY", reviewed_at="2026-11-07")
        case["source_sha256"] = "a" * 64
    path = tmp_path / "benchmark.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    report = run_scientific_evaluation(path, FIXTURES / "summaries-accurate.json")
    assert [report["cohorts"][key]["case_count"] for key in ("verified", "synthetic", "unreviewed")] == [1, 5, 1]
    assert report["cohorts"]["verified"]["coverage_proxy"]["overall"]["denominator"] == 5
    assert report["cohorts"]["verified"]["human_supported_fraction"]["value"] is None


@pytest.mark.parametrize("mutation", ["synthetic_verified", "missing_reviewer", "bad_evidence", "duplicate_id", "wrong_version"])
def test_invalid_benchmark_rejected(mutation):
    data = copy.deepcopy(DATA)
    case = data["cases"][0]
    if mutation == "synthetic_verified":
        case["review"]["status"] = "verified"
    elif mutation == "missing_reviewer":
        case["kind"] = "real"
        case["review"]["status"] = "verified"
    elif mutation == "bad_evidence":
        case["annotations"][0]["evidence_ids"] = ["missing"]
    elif mutation == "duplicate_id":
        data["cases"].append(case)
    else:
        data["schema_version"] = "2.0"
    with pytest.raises(ValidationError):
        Benchmark.model_validate(data)


def test_offline_reproducible_and_no_mutations(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network is forbidden")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    before = {p: p.read_bytes() for p in FIXTURES.glob("*.json")}
    assert run() == run()
    assert before == {p: p.read_bytes() for p in FIXTURES.glob("*.json")}


def test_legacy_url_matching_missing_summaries_and_duplicates(tmp_path):
    summaries = json.loads((FIXTURES / "summaries-accurate.json").read_text())
    summaries = [{k: v for k, v in summaries[0].items() if k != "case_id"}]
    path = tmp_path / "summaries.json"
    path.write_text(json.dumps(summaries))
    report = run_scientific_evaluation(FIXTURES / "benchmark.json", path)
    assert report["evaluated_count"] == 1
    assert report["cases"][1]["missing_or_unassessable"] == ["summary"]
    path.write_text(json.dumps(summaries * 2))
    with pytest.raises(ValueError, match="Ambiguous"):
        run_scientific_evaluation(FIXTURES / "benchmark.json", path)


def test_negative_report_never_hides_errors():
    report = run("negative")
    group = report["cohorts"]["synthetic"]
    assert group["cases_with_known_errors"] == 7
    assert group["quantitative_reference_agreement"]["value"] == 0
    assert group["quantitative_counts"]["failed"] == 3


@pytest.mark.parametrize("status", ["supported", "contradicted", "insufficient_evidence", "not_assessed"])
def test_review_statuses_and_stale_benchmark_rejection(tmp_path, status):
    case = BENCHMARK.cases[0]
    assessment = dict(case_id=case.id, benchmark_sha256=canonical_hash(DATA),
                      summary_sha256=fingerprint(case.reference_summary), reviewer="TEST ONLY",
                      reviewed_at="2026-11-07", claims=[dict(claim=case.annotations[0].statement,
                      status=status, evidence_ids=["E1"], rationale="Test of review transport, not an adjudication")])
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps([assessment]))
    report = run(assessments_path=path)
    assert report["cases"][0]["evidence_support"][0]["status"] == status
    assert report["cohorts"]["verified"]["case_count"] == 0
    assessment["benchmark_sha256"] = "0" * 64
    path.write_text(json.dumps([assessment]))
    with pytest.raises(ValueError, match="benchmark revision"):
        run(assessments_path=path)


def test_schema_export_is_current():
    exported = json.loads((FIXTURES / "benchmark.schema.json").read_text())
    assert exported == Benchmark.model_json_schema()


def test_cli_works_without_loading_scientific_runtime(tmp_path):
    source = Path(__file__).resolve().parents[1] / "src"
    script = f'''
import sys, socket, runpy
sys.path.insert(0, {str(source)!r})
def blocked(*args, **kwargs):
    raise AssertionError('Offline evaluation attempted network access')
socket.socket.connect = blocked
socket.create_connection = blocked
sys.argv = ['scientific', '--benchmark', {str(FIXTURES / 'benchmark.json')!r},
            '--summaries', {str(FIXTURES / 'summaries-accurate.json')!r},
            '--timestamp', '2026-11-07T00:00:00Z']
runpy.run_module('evaluation.scientific', run_name='__main__')
assert not any(name in sys.modules for name in ('torch', 'ollama', 'sentence_transformers'))
'''
    result = subprocess.run([sys.executable, "-c", script], cwd=tmp_path, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert json.loads(result.stdout)["evaluated_count"] == 7
    assert not list(tmp_path.iterdir())
