from triage.filtering import filter_relevant_papers
from triage.topics import passes_topic_precision_gate


def test_method_topic_requires_chemistry_domain_signal():
    paper = {
        "title": "Conformal prediction for medical image segmentation",
        "abstract": "The method improves uncertainty calibration for clinical image segmentation.",
        "url": "https://example.org/imaging",
        "source": "fixture",
    }

    assert not passes_topic_precision_gate(paper, "Uncertainty Quantification")


def test_active_learning_near_miss_does_not_pass_filter(monkeypatch):
    papers = [
        {
            "title": "Active learning for traffic routing",
            "abstract": "A batch active learning method improves routing decisions in urban traffic.",
            "url": "https://example.org/routing",
            "source": "fixture",
        },
        {
            "title": "Active learning for molecular property prediction",
            "abstract": "A cheminformatics workflow uses active learning and molecular graph neural networks for drug discovery.",
            "url": "https://example.org/molecular",
            "source": "fixture",
        },
    ]

    monkeypatch.setattr("triage.filtering.encode_texts", lambda texts: [[0.3] for _ in texts])
    monkeypatch.setattr("triage.filtering.cosine_similarity", lambda a, b: float(a[0]))

    filtered = filter_relevant_papers(papers, fallback_min_results=2)

    assert [paper["url"] for paper in filtered] == ["https://example.org/molecular"]
