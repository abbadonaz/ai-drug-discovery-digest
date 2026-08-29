from digest_core.models import PipelineSettings
from triage.clustering import cluster_and_select_papers, cluster_papers


def test_cluster_papers_adds_representativeness_metadata(monkeypatch):
    papers = [
        {
            "title": "Docking benchmark",
            "abstract": "Virtual screening and docking.",
            "url": "https://example.org/a",
            "topic": "Drug Discovery & Cheminformatics",
            "relevance_score": 0.9,
        },
        {
            "title": "Active learning for molecules",
            "abstract": "Active learning for molecular property prediction.",
            "url": "https://example.org/b",
            "topic": "Bayesian Optimization & Active Learning",
            "relevance_score": 0.8,
        },
    ]

    monkeypatch.setattr("triage.clustering.encode_texts", lambda texts: [[1.0, 0.0], [0.0, 1.0]])
    monkeypatch.setattr("triage.clustering.cosine_similarity", lambda a, b: 1.0)

    clustered = cluster_papers(papers)

    assert all("cluster_id" in paper for paper in clustered)
    assert all("representativeness_score" in paper for paper in clustered)
    assert all("selection_score" in paper for paper in clustered)


def test_cluster_selection_keeps_representatives_first(monkeypatch):
    papers = [
        {
            "title": f"Molecular paper {index}",
            "abstract": "Molecular property prediction for drug discovery.",
            "url": f"https://example.org/{index}",
            "topic": "QSAR & ADMET",
            "relevance_score": 1.0 - index * 0.1,
        }
        for index in range(4)
    ]

    monkeypatch.setattr("triage.clustering.encode_texts", lambda texts: [[1.0, index / 10] for index, _ in enumerate(texts)])
    monkeypatch.setattr("triage.clustering.cosine_similarity", lambda a, b: 1.0)

    clustered, ordered = cluster_and_select_papers(papers, PipelineSettings(max_featured_papers=2))

    assert len(clustered) == 4
    assert ordered[0]["selection_score"] >= ordered[1]["selection_score"]
