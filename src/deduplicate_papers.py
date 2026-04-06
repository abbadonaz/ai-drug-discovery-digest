from utils import load_json, save_json


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


def mark_papers_seen(papers):
    archive = load_archive()

    for paper in papers:
        url = paper.get("url")
        if url:
            archive[url] = True

    save_archive(archive)


def filter_new_papers(papers):
    new_papers, _ = split_new_and_seen_papers(papers)
    mark_papers_seen(new_papers)
    return new_papers
