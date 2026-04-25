from evidence_selector import build_summary_payload, select_relevant_evidence, select_summary_evidence


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
    findings = [item for item in evidence if item["role"] == "findings"]
    assert findings
    assert findings[0]["section"] == "results"
    assert "binding affinity" in findings[0]["text"].lower()


def test_build_summary_payload_formats_evidence_lines(monkeypatch):
    monkeypatch.setattr(
        "evidence_selector.select_summary_evidence",
        lambda paper, max_items=4: [
            {
                "summary_role": "result",
                "role": "findings",
                "section": "results",
                "text": "The method improved docking accuracy.",
            },
            {
                "summary_role": "overview",
                "role": "problem",
                "section": "conclusion",
                "text": "The approach is useful for screening.",
            },
        ],
    )

    payload = build_summary_payload(
        {"title": "Example", "url": "https://example.org/paper", "topic": "Docking"}
    )

    assert "[Result | Results] The method improved docking accuracy." in payload["summary_input"]
    assert "[Overview | Conclusion] The approach is useful for screening." in payload["summary_input"]


def test_select_summary_evidence_prefers_title_aligned_study_sentences_from_abstract():
    paper = {
        "title": "Predictive Modeling of Natural Medicinal Compounds for Alzheimer Disease Using Cheminformatics",
        "url": "https://example.org/paper",
        "sections": {
            "abstract": (
                "Neurodegeneration remains a major therapeutic challenge with no definitive cure. "
                "This study presents a predictive cheminformatics-based model for identifying natural medicinal compounds with potential therapeutic efficacy against Alzheimer disease. "
                "A Random Forest classifier identified 73 candidate compounds after screening more than 7000 molecules from natural-product databases."
            ),
        },
        "sentences": [],
    }

    evidence = select_summary_evidence(paper)

    assert evidence

    overview = next(item for item in evidence if item["summary_role"] == "overview")
    assert "predictive cheminformatics-based model" in overview["text"].lower()
    assert "therapeutic challenge" not in overview["text"].lower()
    assert len(evidence) >= 2
