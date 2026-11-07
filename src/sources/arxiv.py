import logging

import arxiv
from triage.taxonomy import build_arxiv_query
from sources.dates import PublicationWindow, parse_publication_date
from sources.outcomes import eligible_result, error_diagnostic


QUERY = build_arxiv_query()
logger = logging.getLogger(__name__)


def _normalize_datetime(dt):
    parsed, error = parse_publication_date(dt)
    if error:
        raise ValueError(error)
    return parsed


def fetch_arxiv_papers(days_back=7, max_results=40, *, reference_time=None):
    papers = []
    window = PublicationWindow.recent(days_back, reference_time)
    errors = []

    try:
        client = arxiv.Client(page_size=25, delay_seconds=5, num_retries=3)
        search = arxiv.Search(
            query=QUERY, max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )
        for result in client.results(search):
            published = result.published

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
                "published": published.isoformat() if hasattr(published, "isoformat") else published or "",
                "updated": result.updated.isoformat() if getattr(result, "updated", None) else "",
                "source": "arxiv",
            })
    except Exception as error:
        errors.append(error_diagnostic("arxiv.results", error))

    return eligible_result(papers, window, source="arxiv", errors=errors, completed=not errors)


if __name__ == "__main__":
    papers = fetch_arxiv_papers()
    print("\nSample papers:\n")
    for paper in papers[:5]:
        print("-", paper["title"])
