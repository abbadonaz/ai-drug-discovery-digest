from digest_core.env_check import check_environment


def test_environment_check_reports_status():
    result = check_environment()

    assert "python" in result
    assert "missing" in result
    assert "uv sync --extra dev" in result["setup"]
