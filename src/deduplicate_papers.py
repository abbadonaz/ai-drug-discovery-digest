import json
import os

ARCHIVE_FILE = "data/paper_archive.json"


def load_archive():

    if not os.path.exists(ARCHIVE_FILE):
        return {}

    with open(ARCHIVE_FILE, "r") as f:
        return json.load(f)


def save_archive(archive):

    with open(ARCHIVE_FILE, "w") as f:
        json.dump(archive, f, indent=2)


def filter_new_papers(papers):

    archive = load_archive()

    new_papers = []

    for p in papers:

        if p["url"] not in archive:

            new_papers.append(p)
            archive[p["url"]] = True

    save_archive(archive)

    return new_papers