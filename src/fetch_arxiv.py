from datetime import datetime, timedelta, timezone

import arxiv
from research_taxonomy import build_arxiv_query


QUERY = build_arxiv_query()


def _normalize_datetime(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_arxiv_papers(days_back=7, max_results=40):
    print("Fetching papers from arXiv (safe mode)...")

    client = arxiv.Client(page_size=25, delay_seconds=5, num_retries=3)
    search = arxiv.Search(
        query=QUERY,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )

    papers = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    try:
        for result in client.results(search):
            published = _normalize_datetime(result.published)
            if published < cutoff:
                continue

            title = (result.title or "").strip()
            abstract = (result.summary or "").strip().replace("\n", " ")
            if not title or not abstract or not result.entry_id:
                continue

            papers.append({
                "title": title,
                "authors": [author.name for author in (result.authors or [])],
                "abstract": abstract,
                "url": result.entry_id,
                "pdf_url": getattr(result, "pdf_url", None),
                "published": published.isoformat(),
                "source": "arxiv",
            })
    except Exception as error:
        print(f"Error fetching arXiv: {error}")

    return papers


if __name__ == "__main__":
    papers = fetch_arxiv_papers()
    print("\nSample papers:\n")
    for paper in papers[:5]:
        print("-", paper["title"])
