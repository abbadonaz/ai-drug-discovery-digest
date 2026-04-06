from llm_summarizer import summarize_papers
import llm_summarizer


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
    assert "Fallback note" in summaries[0]["tldr"]
    assert "### Problem" in summaries[0]["tldr"]


def test_ollama_chat_uses_fallback_model_on_memory_error(monkeypatch):
    calls = []

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
