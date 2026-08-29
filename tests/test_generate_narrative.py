from digest_core.config import MAX_NARRATIVE_CONTEXT_CHARS, MAX_NARRATIVE_PAPERS
from summarization.narrative import build_trend_input, generate_weekly_narrative


def test_generate_weekly_narrative_uses_fallback_model_on_memory_error(monkeypatch):
    calls = []
    monkeypatch.setattr("summarization.ollama_client.get_installed_model_names", lambda: ())

    def fake_chat(model, messages, options):
        calls.append(model)
        if len(calls) == 1:
            raise RuntimeError(
                "model requires more system memory (3.2 GiB) than is available (3.1 GiB) (status code: 500)"
            )
        return {"message": {"content": "editorial intro"}}

    monkeypatch.setattr("summarization.narrative.ollama.chat", fake_chat)

    text = generate_weekly_narrative([
        {
            "title": "Example",
            "topic": "Molecular Representation Learning",
            "tldr": "A summary.",
        }
    ])

    assert text == "editorial intro"
    assert len(calls) == 2


def test_build_trend_input_limits_prompt_size():
    summaries = [
        {
            "title": f"Paper {index}",
            "topic": f"Topic {index}",
            "tldr": "A" * 1200,
        }
        for index in range(MAX_NARRATIVE_PAPERS + 3)
    ]

    context = build_trend_input(summaries)

    assert context.count("Topic: ") == MAX_NARRATIVE_PAPERS
    assert len(context) <= MAX_NARRATIVE_CONTEXT_CHARS
