import arxiv
from datetime import datetime, timedelta, timezone


# Broader query aimed at pharma R&D / molecular ML / computational chemistry
QUERY = """
(
    ti:"drug discovery" OR abs:"drug discovery" OR
    ti:cheminformatics OR abs:cheminformatics OR
    ti:"molecular docking" OR abs:"molecular docking" OR
    ti:docking OR abs:docking OR
    ti:"virtual screening" OR abs:"virtual screening" OR
    ti:qsar OR abs:qsar OR
    ti:admet OR abs:admet OR
    ti:"binding affinity" OR abs:"binding affinity" OR
    ti:"structure-based drug design" OR abs:"structure-based drug design" OR
    ti:"computational chemistry" OR abs:"computational chemistry" OR
    ti:"generative model" OR abs:"generative model" OR
    ti:"generative chemistry" OR abs:"generative chemistry" OR
    ti:"molecular generation" OR abs:"molecular generation" OR
    ti:reinvent OR abs:reinvent OR
    ti:"bayesian optimization" OR abs:"bayesian optimization" OR
    ti:"active learning" OR abs:"active learning" OR
    ti:"uncertainty quantification" OR abs:"uncertainty quantification" OR
    ti:"molecular representation" OR abs:"molecular representation" OR
    ti:"graph neural network" OR abs:"graph neural network"
)
AND
(
    cat:q-bio.QM OR
    cat:cs.LG OR
    cat:stat.ML OR
    cat:physics.chem-ph
)
"""


def _normalize_datetime(dt):
    """Ensure datetime is timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_arxiv_papers(days_back=14, max_results=500):
    """
    Fetch recent arXiv papers likely relevant to drug discovery / cheminformatics / molecular ML.
    """

    client = arxiv.Client(
        page_size=100,
        delay_seconds=3,
        num_retries=3,
    )

    search = arxiv.Search(
        query=QUERY,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )

    papers = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    for result in client.results(search):
        published = _normalize_datetime(result.published)

        if published < cutoff:
            continue

        papers.append(
            {
                "title": result.title.strip(),
                "authors": [a.name for a in result.authors],
                "abstract": result.summary.strip().replace("\n", " "),
                "url": result.entry_id,
                "pdf_url": result.pdf_url,
                "published": published.isoformat(),
                "primary_category": getattr(result, "primary_category", None),
                "categories": list(getattr(result, "categories", [])),
            }
        )

    return papers


if __name__ == "__main__":
    papers = fetch_arxiv_papers()

    print(f"Fetched {len(papers)} papers")

    for p in papers[:10]:
        print("-", p["title"])