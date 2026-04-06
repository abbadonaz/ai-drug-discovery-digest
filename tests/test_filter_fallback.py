from filter_papers import filter_relevant_papers


def test_filter_relevant_papers_keeps_top_candidates_when_strict_gate_is_empty(monkeypatch):
    papers = [
        {
            "title": "Docking workflow for lead optimization",
            "abstract": "A virtual screening and docking benchmark for drug discovery.",
            "url": "https://example.org/1",
        },
        {
            "title": "General machine learning paper",
            "abstract": "A broad method paper with weak domain signal.",
            "url": "https://example.org/2",
        },
    ]

    monkeypatch.setattr(
        "filter_papers.encode_texts",
        lambda texts: [[0.1], [0.09], [0.2]] if len(texts) == 2 else [[0.2]],
    )
    monkeypatch.setattr(
        "filter_papers.cosine_similarity",
        lambda a, b: float(a[0]),
    )

    filtered = filter_relevant_papers(
        papers,
        threshold=0.95,
        strong_semantic_threshold=0.9,
        fallback_min_results=1,
    )

    assert len(filtered) == 1
    assert filtered[0]["title"] == "Docking workflow for lead optimization"


def test_filter_relevant_papers_prefers_field_relevance_over_generic_biomedical_docking(monkeypatch):
    papers = [
        {
            "title": "Computational design strategies for lead optimization",
            "abstract": "A drug discovery study using virtual screening, computational chemistry, and molecular dynamics.",
            "url": "https://example.org/1",
        },
        {
            "title": "Cancer biomarker study with molecular docking validation",
            "abstract": "Gene expression, prognosis, and immune infiltration were analyzed and later validated with docking.",
            "url": "https://example.org/2",
        },
    ]

    monkeypatch.setattr(
        "filter_papers.encode_texts",
        lambda texts: [[0.31], [0.24]] if len(texts) == 2 else [[0.3]],
    )
    monkeypatch.setattr(
        "filter_papers.cosine_similarity",
        lambda a, b: float(a[0]),
    )

    filtered = filter_relevant_papers(papers, fallback_min_results=2)

    assert filtered
    assert filtered[0]["title"] == "Computational design strategies for lead optimization"
    assert all("biomarker study" not in paper["title"].lower() for paper in filtered[:1])
