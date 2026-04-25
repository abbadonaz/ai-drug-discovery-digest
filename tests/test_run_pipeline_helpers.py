from run_pipeline import build_featured_paper_record


def test_build_featured_paper_record_falls_back_to_abstract(monkeypatch):
    paper = {
        "title": "Example paper",
        "url": "https://example.org/paper",
        "topic": "Drug Discovery & Cheminformatics",
        "abstract": (
            "Virtual screening remains a bottleneck in lead discovery. "
            "This study combines docking with molecular dynamics refinement to reprioritize candidates. "
            "Benchmark evaluation shows improved enrichment over reference baselines."
        ),
    }

    monkeypatch.setattr("run_pipeline.download_pdf", lambda paper: None)
    monkeypatch.setattr("run_pipeline.has_sufficient_summary_evidence", lambda record: True)

    record = build_featured_paper_record(paper)

    assert record is not None
    assert record["sections"]["abstract"] == paper["abstract"]
    assert record["sentences"]


def test_build_featured_paper_record_rejects_title_only_abstract(monkeypatch):
    paper = {
        "title": "Example paper",
        "url": "https://example.org/paper",
        "topic": "Drug Discovery & Cheminformatics",
        "abstract": "Example paper",
    }

    monkeypatch.setattr("run_pipeline.download_pdf", lambda paper: None)

    assert build_featured_paper_record(paper) is None
