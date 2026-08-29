import argparse
import json
from pathlib import Path
import sys

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from digest_core.utils import load_json
from summarization.llm import summary_quality_issues
from triage.filtering import filter_relevant_papers
from triage.scoring import rank_papers


DEFAULT_FIXTURE = Path("tests/fixtures/evaluation_papers.json")


def evaluate_relevance(papers):
    filtered = filter_relevant_papers(papers, fallback_min_results=len(papers))
    ranked_urls = [paper["url"] for paper in filtered]
    expected_urls = [paper["url"] for paper in papers if paper.get("expected_relevant")]
    hits = [url for url in expected_urls if url in ranked_urls[: len(expected_urls)]]

    return {
        "expected_relevant": len(expected_urls),
        "retrieved": len(filtered),
        "top_k_recall": len(hits) / len(expected_urls) if expected_urls else 1.0,
        "top_urls": ranked_urls[:5],
    }


def evaluate_summary_quality(summaries):
    checked = []

    for summary in summaries:
        issues = summary_quality_issues(summary.get("tldr", ""))
        checked.append({
            "title": summary.get("title", ""),
            "issues": issues,
            "passed": not issues,
        })

    passed = sum(1 for item in checked if item["passed"])
    return {
        "checked": len(checked),
        "passed": passed,
        "pass_rate": passed / len(checked) if checked else 1.0,
        "items": checked,
    }


def run_evaluation(fixture_path=DEFAULT_FIXTURE):
    fixture = load_json(fixture_path, default={})
    papers = fixture.get("papers", [])
    summaries = fixture.get("summaries", [])

    relevance = evaluate_relevance(papers)
    summary_quality = evaluate_summary_quality(rank_papers(summaries))

    return {
        "fixture": str(fixture_path),
        "relevance": relevance,
        "summary_quality": summary_quality,
    }


def main():
    parser = argparse.ArgumentParser(description="Run offline digest quality checks.")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    args = parser.parse_args()

    result = run_evaluation(Path(args.fixture))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
