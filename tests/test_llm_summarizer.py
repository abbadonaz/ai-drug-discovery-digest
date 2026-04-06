from llm_summarizer import summarize_papers


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
