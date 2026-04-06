from deduplicate_papers import mark_papers_seen, split_new_and_seen_papers


def test_split_new_and_seen_papers_separates_already_seen_entries(tmp_path, monkeypatch):
    archive_path = tmp_path / "paper_archive.json"
    monkeypatch.setattr("deduplicate_papers.ARCHIVE_FILE", str(archive_path))

    seen = [{"url": "https://example.org/seen", "title": "Seen"}]
    mark_papers_seen(seen)

    new_papers, seen_papers = split_new_and_seen_papers([
        {"url": "https://example.org/seen", "title": "Seen"},
        {"url": "https://example.org/new", "title": "New"},
    ])

    assert [paper["url"] for paper in new_papers] == ["https://example.org/new"]
    assert [paper["url"] for paper in seen_papers] == ["https://example.org/seen"]
