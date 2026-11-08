import json
from pathlib import Path

import pytest

from evaluation.checkpoint import CheckpointChat, replay_lock, write_once
from evaluation.full_text_replay import replay


def test_completed_raw_response_is_reused_without_inference(tmp_path):
    calls = []

    def chat(**kwargs):
        calls.append(kwargs)
        return {"model": "mistral:latest", "message": {"content": "response"}}

    prefix = tmp_path / "paper-1-legacy"
    first = CheckpointChat(prefix, "mistral:latest", 900, chat)
    assert first("prompt") == "response"
    resumed = CheckpointChat(prefix, "mistral:latest", 900, chat)
    assert resumed("prompt") == "response"
    assert len(calls) == 1
    assert resumed.calls[0]["parameters"] == {"temperature": .2, "num_predict": 900}
    assert resumed.calls[0]["elapsed_seconds"] >= 0


def test_publication_never_replaces_a_checkpoint(tmp_path):
    target = tmp_path / "result.json"
    write_once(target, {"successful": True})
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        write_once(target, {"successful": False})
    assert target.read_bytes() == original
    assert list(tmp_path.iterdir()) == [target]


def test_invalid_raw_json_survives_parsing_failure_and_is_not_regenerated(tmp_path):
    calls = []

    def chat(**kwargs):
        calls.append(kwargs)
        return {"message": {"content": "malformed JSON"}}

    for _ in range(2):
        checkpoint = CheckpointChat(tmp_path / "run", "mistral:latest", 900, chat)
        with pytest.raises(json.JSONDecodeError):
            json.loads(checkpoint("prompt"))
    assert len(calls) == 1


def test_http_500_is_recorded_and_never_retried(tmp_path):
    calls = []

    class ServerError(Exception):
        status_code = 500

    def chat(**kwargs):
        calls.append(kwargs)
        raise ServerError("runner stopped")

    checkpoint = CheckpointChat(tmp_path / "run", "mistral:latest", 900, chat)
    for _ in range(2):
        with pytest.raises(ServerError):
            checkpoint("prompt")
    assert len(calls) == 1
    failure, = tmp_path.glob("*-failure-*.json")
    assert json.loads(failure.read_text())["status_code"] == 500
    assert not list(tmp_path.glob("*-response-*.json"))
    with pytest.raises(RuntimeError, match="Previous failure checkpoint"):
        CheckpointChat(tmp_path / "run", "mistral:latest", 900, chat)("prompt")
    assert len(calls) == 1


def test_changed_generation_settings_do_not_reuse_raw_output(tmp_path):
    prefix = tmp_path / "run"
    chat = lambda **kwargs: {"model": "mistral:latest", "message": {"content": "response"}}
    CheckpointChat(prefix, "mistral:latest", 900, chat)("prompt")
    with pytest.raises(ValueError, match="settings differ"):
        CheckpointChat(prefix, "mistral:latest", 100, chat)("prompt")


def test_one_condition_cannot_issue_a_second_generation(tmp_path):
    calls = []

    def chat(**kwargs):
        calls.append(kwargs)
        return {"message": {"content": "saved"}}

    checkpoint = CheckpointChat(tmp_path / "run", "mistral:latest", 900, chat)
    checkpoint("first prompt")
    with pytest.raises(ValueError, match="One generation per condition"):
        checkpoint("second prompt")
    assert len(calls) == 1


def test_replay_lock_does_not_steal_existing_lock(tmp_path):
    with replay_lock(tmp_path):
        with pytest.raises(FileExistsError):
            with replay_lock(tmp_path):
                pytest.fail("concurrent replay entered")
        assert (tmp_path / ".replay.lock").exists()
    assert not (tmp_path / ".replay.lock").exists()


@pytest.mark.parametrize("mode,status", [("llm", "completed"), ("extractive_fallback", "completed_invalid_output")])
def test_existing_conditions_skip_builder_and_inference(tmp_path, monkeypatch, mode, status):
    import evaluation.full_text_replay as module

    paper = {"title": "Test", "url": "https://arxiv.org/abs/1234.56789v1",
             "abstract": "Existing abstract", "pdf_path": str(Path(__file__).parent / "fixtures/evidence/scientific-study.pdf")}
    for strategy in ("legacy", "section_aware"):
        write_once(tmp_path / f"paper-1-{strategy}.json", {
            "status": status, "summary": {"url": paper["url"], "generation_mode": mode}})
    monkeypatch.setattr(module.FeaturedPaperEvidenceBuilder, "build_featured_record",
                        lambda *args: pytest.fail("completed condition rebuilt"))
    monkeypatch.setattr(module, "run_scientific_evaluation", lambda *args: {
        "benchmark_version": "test", "evaluated_count": 0, "authoritative_benchmark_available": False})
    report = replay([paper], tmp_path, chat=lambda **kwargs: pytest.fail("completed inference rerun"))
    assert len(report["papers"][0]["runs"]) == 2


def test_replay_stops_after_http_500_even_when_summarizer_catches_it(tmp_path, monkeypatch):
    import evaluation.full_text_replay as module

    calls = []

    class ServerError(Exception):
        status_code = 500

    def chat(**kwargs):
        calls.append(kwargs)
        raise ServerError("failure")

    monkeypatch.setattr(module.FeaturedPaperEvidenceBuilder, "build_featured_record", lambda *args: {})
    monkeypatch.setattr(module, "build_summary_payload", lambda *args: {"evidence": [], "summary_input": "input"})

    def summarize(record):
        for _ in range(2):
            try:
                module.llm._ollama_chat("prompt")
            except Exception:
                pass
        return {"generation_mode": "extractive_fallback"}

    monkeypatch.setattr(module.llm, "summarize_paper_record", summarize)
    paper = {"title": "Test", "url": "https://arxiv.org/abs/1234.56789v1", "abstract": "Existing abstract",
             "pdf_path": str(Path(__file__).parent / "fixtures/evidence/scientific-study.pdf")}
    with pytest.raises(ServerError):
        replay([paper], tmp_path, chat=chat)
    assert len(calls) == 1
    assert not list(tmp_path.glob("paper-*-legacy.json"))
    assert not list(tmp_path.glob("paper-*-section_aware.json"))


def test_unavailable_evidence_is_checkpointed_without_an_inference_call(tmp_path, monkeypatch):
    import evaluation.full_text_replay as module

    paper = {"title": "Test", "url": "https://arxiv.org/abs/1234.56789v1", "abstract": "Existing abstract",
             "pdf_path": str(Path(__file__).parent / "fixtures/evidence/scientific-study.pdf")}
    monkeypatch.setattr(module.FeaturedPaperEvidenceBuilder, "build_featured_record", lambda *args: {})
    monkeypatch.setattr(module, "build_summary_payload", lambda *args: {"evidence": [], "summary_input": ""})
    unavailable = {"generation_mode": "unavailable", "url": paper["url"]}
    monkeypatch.setattr(module.llm, "summarize_paper_record", lambda *args: unavailable)
    monkeypatch.setattr(module, "summarize_scientific", lambda *args, **kwargs: unavailable)
    monkeypatch.setattr(module, "run_scientific_evaluation", lambda *args: {
        "benchmark_version": "test", "evaluated_count": 0, "authoritative_benchmark_available": False})
    report = replay([paper], tmp_path, chat=lambda **kwargs: pytest.fail("empty evidence inferred"))
    for run in report["papers"][0]["runs"].values():
        assert run["model_identity"] is None
        assert run["generation_seconds"] == 0
        assert run["status"] == "completed_invalid_output"
    replay([paper], tmp_path, chat=lambda **kwargs: pytest.fail("unavailable condition rerun"))
