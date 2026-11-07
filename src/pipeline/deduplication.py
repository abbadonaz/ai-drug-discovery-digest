from digest_core.utils import load_json, save_json
import json
from pathlib import Path


ARCHIVE_FILE = "data/paper_archive.json"


def load_archive():
    archive = load_json(ARCHIVE_FILE, default={})
    return archive if isinstance(archive, dict) else {}


def save_archive(archive):
    save_json(archive, ARCHIVE_FILE)


def split_new_and_seen_papers(papers):
    archive = load_archive()
    new_papers = []
    seen_papers = []

    for paper in papers:
        url = paper.get("url")
        if not url:
            continue

        if url not in archive:
            new_papers.append(paper)
        else:
            seen_papers.append(paper)

    return new_papers, seen_papers


def archive_with_seen(papers):
    """Prepare state without writing; never overwrite unreadable prior history."""
    path = Path(ARCHIVE_FILE)
    archive = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(archive, dict):
        raise ValueError("Seen-paper history must be a JSON object")

    for paper in papers:
        url = paper.get("url")
        if url:
            archive[url] = True

    return archive


def mark_papers_seen(papers):
    save_archive(archive_with_seen(papers))


def filter_new_papers(papers):
    new_papers, _ = split_new_and_seen_papers(papers)
    mark_papers_seen(new_papers)
    return new_papers
