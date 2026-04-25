from llm_summarizer import summarize_papers
import llm_summarizer
from config import OLLAMA_FALLBACK_NUM_PREDICT, SECONDARY_FALLBACK_MODEL_NAME


def test_summarize_papers_uses_extractive_fallback_when_ollama_fails(monkeypatch):
    monkeypatch.setattr(
        "llm_summarizer.summarize_paper",
        lambda paper: (_ for _ in ()).throw(RuntimeError("runner crashed")),
    )

    papers = [{
        "title": "Example paper",
        "url": "https://example.org/paper",
        "topic": "Drug Discovery & Cheminformatics",
        "sentences": [
            "This study develops a virtual screening workflow for drug discovery.",
            "The method uses molecular dynamics and docking to refine candidate ranking.",
            "Benchmark evaluation shows improved enrichment over reference baselines.",
        ],
        "context": "This study develops a virtual screening workflow for drug discovery.",
        "sections": {
            "abstract": "This study develops a virtual screening workflow for drug discovery.",
            "results": "Benchmark evaluation shows improved enrichment over reference baselines.",
        },
    }]

    summaries = summarize_papers(papers)

    assert len(summaries) == 1
    assert "virtual screening workflow" in summaries[0]["tldr"].lower()
    assert "###" not in summaries[0]["tldr"]


def test_ollama_chat_uses_fallback_model_on_memory_error(monkeypatch):
    calls = []
    monkeypatch.setattr("ollama_client.get_installed_model_names", lambda: ())

    def fake_chat(model, messages, options):
        calls.append((model, options["num_predict"]))
        if model == llm_summarizer.MODEL_NAME:
            raise RuntimeError(
                "model requires more system memory (3.2 GiB) than is available (3.1 GiB) (status code: 500)"
            )
        return {"message": {"content": "fallback summary"}}

    monkeypatch.setattr("llm_summarizer.ollama.chat", fake_chat)

    result = llm_summarizer._ollama_chat("test prompt", max_retries=0)

    assert result == "fallback summary"
    assert calls[0][0] == llm_summarizer.MODEL_NAME
    assert calls[1][0] == llm_summarizer.FALLBACK_MODEL_NAME
    assert calls[1][1] == OLLAMA_FALLBACK_NUM_PREDICT


def test_ollama_chat_uses_secondary_fallback_when_first_two_models_oom(monkeypatch):
    calls = []
    monkeypatch.setattr("ollama_client.get_installed_model_names", lambda: ())

    def fake_chat(model, messages, options):
        calls.append(model)
        if model != SECONDARY_FALLBACK_MODEL_NAME:
            raise RuntimeError(
                "model requires more system memory (3.2 GiB) than is available (3.1 GiB) (status code: 500)"
            )
        return {"message": {"content": "secondary fallback summary"}}

    monkeypatch.setattr("llm_summarizer.ollama.chat", fake_chat)

    result = llm_summarizer._ollama_chat("test prompt", max_retries=0)

    assert result == "secondary fallback summary"
    assert calls == [
        llm_summarizer.MODEL_NAME,
        llm_summarizer.FALLBACK_MODEL_NAME,
        SECONDARY_FALLBACK_MODEL_NAME,
    ]


def test_ollama_chat_uses_fallback_model_when_primary_is_missing(monkeypatch):
    calls = []
    monkeypatch.setattr("ollama_client.get_installed_model_names", lambda: ())

    def fake_chat(model, messages, options):
        calls.append(model)
        if model == llm_summarizer.MODEL_NAME:
            raise RuntimeError(f"model '{model}' not found (status code: 404)")
        return {"message": {"content": "fallback summary"}}

    monkeypatch.setattr("llm_summarizer.ollama.chat", fake_chat)

    result = llm_summarizer._ollama_chat("test prompt", max_retries=0)

    assert result == "fallback summary"
    assert calls[:2] == [
        llm_summarizer.MODEL_NAME,
        llm_summarizer.FALLBACK_MODEL_NAME,
    ]


def test_ollama_chat_uses_fallback_model_when_primary_runner_crashes(monkeypatch):
    calls = []
    monkeypatch.setattr("ollama_client.get_installed_model_names", lambda: ())

    def fake_chat(model, messages, options):
        calls.append(model)
        if model == llm_summarizer.MODEL_NAME:
            raise RuntimeError(
                "llama runner process has terminated: %!w(<nil>) (status code: 500)"
            )
        return {"message": {"content": "fallback summary"}}

    monkeypatch.setattr("llm_summarizer.ollama.chat", fake_chat)

    result = llm_summarizer._ollama_chat("test prompt", max_retries=0)

    assert result == "fallback summary"
    assert calls[:2] == [
        llm_summarizer.MODEL_NAME,
        llm_summarizer.FALLBACK_MODEL_NAME,
    ]


def test_ollama_chat_uses_installed_model_when_configured_models_are_unavailable(monkeypatch):
    calls = []
    monkeypatch.setattr("ollama_client.get_installed_model_names", lambda: ("mistral:latest", "nomic-embed-text:latest"))

    def fake_chat(model, messages, options):
        calls.append((model, options["num_predict"]))
        return {"message": {"content": "installed-model summary"}}

    monkeypatch.setattr("llm_summarizer.ollama.chat", fake_chat)

    result = llm_summarizer._ollama_chat("test prompt", max_retries=0)

    assert result == "installed-model summary"
    assert calls[0][0] == "mistral:latest"
    assert all("embed" not in model for model, _ in calls)


def test_summary_quality_issues_detect_incomplete_output():
    issues = llm_summarizer.summary_quality_issues(
        "A partial summary that stops at the"
    )

    assert any("too few sentences" in issue for issue in issues)
    assert any("ending" in issue for issue in issues)


def test_summarize_with_llm_retries_when_first_output_is_truncated(monkeypatch):
    calls = []
    valid_summary = (
        "Reliable ranking is hard in low-data settings. "
        "The method calibrates judge scores and improves trust signals. "
        "The approach gives a grounded deployment signal."
    )

    def fake_chat(prompt, max_retries=1, num_predict=None):
        calls.append(num_predict)
        if len(calls) == 1:
            return "Partial output that stops at the"
        return valid_summary

    monkeypatch.setattr("llm_summarizer._ollama_chat", fake_chat)

    result = llm_summarizer.summarize_with_llm(
        "Example paper",
        "[Problem | Abstract] Reliable ranking is hard.",
    )

    assert result == valid_summary
    assert calls[0] == min(llm_summarizer.OLLAMA_NUM_PREDICT, 180)
    assert calls[1] >= 180


def test_summarize_paper_falls_back_when_summary_is_invalid(monkeypatch):
    monkeypatch.setattr(
        "llm_summarizer.build_summary_payload",
        lambda paper: {
            "title": paper["title"],
            "url": paper["url"],
            "topic": paper["topic"],
            "summary_input": "[Overview | Abstract] A grounded source sentence. [Result | Results] The model improves docking accuracy on a benchmark.",
            "context": "A grounded source sentence. The model improves docking accuracy on a benchmark.",
            "evidence": [
                {"summary_role": "overview", "role": "problem", "section": "abstract", "text": "A grounded source sentence."},
                {"summary_role": "result", "role": "findings", "section": "results", "text": "The model improves docking accuracy on a benchmark."},
            ],
        },
    )
    monkeypatch.setattr(
        "llm_summarizer.summarize_with_llm",
        lambda title, summary_input: "### Problem\nIncomplete summary that ends with the",
    )

    summary = llm_summarizer.summarize_paper({
        "title": "Example paper",
        "url": "https://example.org/paper",
        "topic": "Drug Discovery & Cheminformatics",
        "sentences": ["A grounded source sentence."],
    })

    assert "A grounded source sentence." in summary
    assert "benchmark" in summary.lower()
    assert "###" not in summary
