import feedparser
from datetime import datetime, timedelta


CHEMRXIV_RSS = "https://chemrxiv.org/engage/chemrxiv/rss"


KEYWORDS = [
    "drug",
    "docking",
    "virtual screening",
    "ligand",
    "protein",
    "qsar",
    "admet",
    "binding",
    "cheminformatics",
    "generative",
    "molecular design",
    "molecular generation",
    "reinvent",
    "active learning",
    "bayesian optimization",
    "uncertainty",
]


def keyword_match(text):

    text = text.lower()

    for k in KEYWORDS:
        if k in text:
            return True

    return False


def fetch_chemrxiv_papers(days_back=14):

    feed = feedparser.parse(CHEMRXIV_RSS)

    papers = []

    cutoff = datetime.utcnow() - timedelta(days=days_back)

    for entry in feed.entries:

        if not hasattr(entry, "published_parsed"):
            continue

        published = datetime(*entry.published_parsed[:6])

        if published < cutoff:
            continue

        title = entry.title
        summary = entry.summary

        text = f"{title} {summary}"

        if not keyword_match(text):
            continue

        paper = {
            "title": title,
            "abstract": summary,
            "url": entry.link,
            "source": "chemrxiv",
            "published": published.isoformat()
        }

        papers.append(paper)

    return papers


if __name__ == "__main__":

    papers = fetch_chemrxiv_papers()

    print(f"Fetched {len(papers)} ChemRxiv papers")

    for p in papers[:5]:
        print("-", p["title"])