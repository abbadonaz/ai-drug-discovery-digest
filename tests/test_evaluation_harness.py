from evaluation.harness import run_evaluation


def test_evaluation_harness_runs_against_fixture():
    result = run_evaluation()

    assert result["relevance"]["expected_relevant"] == 2
    assert result["summary_quality"]["checked"] == 2
