from pathlib import Path

from digest_core.utils import load_json


def test_load_json_returns_default_for_empty_file(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("", encoding="utf-8")

    assert load_json(path, default={}) == {}


def test_load_json_returns_default_and_preserves_corrupt_backup(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not-valid-json", encoding="utf-8")

    result = load_json(path, default=[])

    assert result == []
    assert Path(str(path) + ".corrupt").exists()
