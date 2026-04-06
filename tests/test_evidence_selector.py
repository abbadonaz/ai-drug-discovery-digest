from evidence_selector import build_summary_payload, select_relevant_evidence


def test_select_relevant_evidence_prioritizes_results_and_domain_language(monkeypatch):
    monkeypatch.setattr(
        "evidence_selector.encode_texts",
        lambda texts: [[float(index + 1)] for index, _ in enumerate(texts)],
    )
    monkeypatch.setattr(
        "evidence_selector.cosine_similarity",
        lambda a, b: float(a[0]),
    )

    paper = {
        "title": "Example",
        "url": "https://example.org/paper",
        "sections": {
            "introduction": "This study explores chemistry tasks in a general setting. " * 4,
            "results": (
                "The docking model improved binding affinity prediction and outperformed baselines on the benchmark. "
                "AUC improved substantially across the virtual screening task. "
            ),
        },
    }

    evidence = select_relevant_evidence(paper, top_k=2)

    assert evidence
    assert evidence[0]["section"] == "results"
    assert "binding affinity" in evidence[0]["text"].lower()


def test_build_summary_payload_formats_evidence_lines(monkeypatch):
    monkeypatch.setattr(
        "evidence_selector.select_relevant_evidence",
        lambda paper, top_k=12: [
            {"section": "results", "text": "The method improved docking accuracy."},
            {"section": "conclusion", "text": "The approach is useful for screening."},
        ],
    )

    payload = build_summary_payload(
        {"title": "Example", "url": "https://example.org/paper", "topic": "Docking"}
    )

    assert "[Results] The method improved docking accuracy." in payload["summary_input"]
    assert "[Conclusion] The approach is useful for screening." in payload["summary_input"]
