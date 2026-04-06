from run_pipeline import build_featured_paper_record


def test_build_featured_paper_record_falls_back_to_abstract(monkeypatch):
    paper = {
        "title": "Example paper",
        "url": "https://example.org/paper",
        "topic": "Drug Discovery & Cheminformatics",
        "abstract": "This abstract describes virtual screening for drug discovery and molecular dynamics for lead optimization.",
    }

    monkeypatch.setattr("run_pipeline.download_pdf", lambda paper: None)

    record = build_featured_paper_record(paper)

    assert record is not None
    assert record["sections"]["abstract"] == paper["abstract"]
    assert record["sentences"]
