from triage.filtering import filter_relevant_papers
from triage.scoring import rank_papers


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
        "triage.filtering.encode_texts",
        lambda texts: [[0.1], [0.09], [0.2]] if len(texts) == 2 else [[0.2]],
    )
    monkeypatch.setattr(
        "triage.filtering.cosine_similarity",
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
        "triage.filtering.encode_texts",
        lambda texts: [[0.31], [0.24]] if len(texts) == 2 else [[0.3]],
    )
    monkeypatch.setattr(
        "triage.filtering.cosine_similarity",
        lambda a, b: float(a[0]),
    )

    filtered = filter_relevant_papers(papers, fallback_min_results=2)

    assert filtered
    assert filtered[0]["title"] == "Computational design strategies for lead optimization"
    assert all("biomarker study" not in paper["title"].lower() for paper in filtered[:1])


def test_filter_relevant_papers_prioritizes_ai_cheminformatics_over_broad_chemistry(monkeypatch):
    papers = [
        {
            "title": "Active learning and conformal prediction for molecular property optimization",
            "abstract": "A cheminformatics study on uncertainty quantification, graph neural networks, and molecular representation learning for drug discovery.",
            "url": "https://example.org/ai",
        },
        {
            "title": "Molecular dynamics study of solvent effects in catalytic reaction simulations",
            "abstract": "A computational chemistry paper focused on simulation, reaction mechanisms, and catalysis.",
            "url": "https://example.org/chem",
        },
    ]

    monkeypatch.setattr(
        "triage.filtering.encode_texts",
        lambda texts: [[0.28], [0.26]] if len(texts) == 2 else [[0.3]],
    )
    monkeypatch.setattr(
        "triage.filtering.cosine_similarity",
        lambda a, b: float(a[0]),
    )

    filtered = filter_relevant_papers(papers, fallback_min_results=2)

    assert len(filtered) == 2
    assert filtered[0]["url"] == "https://example.org/ai"
    assert filtered[0]["relevance_score"] > filtered[1]["relevance_score"] + 1.0
    assert filtered[0]["topic"] in {
        "Bayesian Optimization & Active Learning",
        "Uncertainty Quantification",
        "Molecular Representation Learning",
    }


def test_rank_papers_prefers_ai_method_topics():
    summaries = [
        {
            "title": "Active learning for molecular representation selection",
            "topic": "Bayesian Optimization & Active Learning",
            "tldr": "Uses active learning, uncertainty quantification, and molecular embeddings in cheminformatics.",
            "url": "https://example.org/ai",
        },
        {
            "title": "Free energy perturbation workflow for protein-ligand systems",
            "topic": "Computational Chemistry",
            "tldr": "A computational chemistry workflow using free energy perturbation for binding affinity analysis.",
            "url": "https://example.org/fep",
        },
    ]

    ranked = rank_papers(summaries)

    assert ranked[0]["url"] == "https://example.org/ai"
