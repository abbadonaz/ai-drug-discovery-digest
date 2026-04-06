from generate_narrative import generate_weekly_narrative


def test_generate_weekly_narrative_uses_fallback_model_on_memory_error(monkeypatch):
    calls = []

    def fake_chat(model, messages, options):
        calls.append(model)
        if len(calls) == 1:
            raise RuntimeError(
                "model requires more system memory (3.2 GiB) than is available (3.1 GiB) (status code: 500)"
            )
        return {"message": {"content": "editorial intro"}}

    monkeypatch.setattr("generate_narrative.ollama.chat", fake_chat)

    text = generate_weekly_narrative([
        {
            "title": "Example",
            "topic": "Molecular Representation Learning",
            "tldr": "A summary.",
        }
    ])

    assert text == "editorial intro"
    assert len(calls) == 2
