import os
import logging
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

from Bio import Entrez
from triage.taxonomy import build_pubmed_query


Entrez.email = os.getenv("ENTREZ_EMAIL", "your_email@example.com")

QUERY = build_pubmed_query()
logger = logging.getLogger(__name__)


def _extract_abstract(article):
    parts = []
    for node in article.findall(".//Abstract/AbstractText"):
        label = node.attrib.get("Label")
        text = "".join(node.itertext()).strip()
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
    return " ".join(parts).strip()


def _extract_publication_date(article):
    year = article.findtext(".//PubDate/Year")
    month = article.findtext(".//PubDate/Month", "1")
    day = article.findtext(".//PubDate/Day", "1")

    month_lookup = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    try:
        month_value = int(month)
    except ValueError:
        month_value = month_lookup.get(month[:3].lower(), 1)

    try:
        return datetime(int(year), int(month_value), int(day), tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def fetch_pubmed_papers(days_back=14, max_results=200):
    try:
        handle = Entrez.esearch(
            db="pubmed",
            term=QUERY,
            retmax=max_results,
            sort="pub date",
        )
        record = Entrez.read(handle)
        ids = record.get("IdList", [])
    except Exception as error:
        logger.warning("Error fetching PubMed IDs: %s", error)
        return []

    if not ids:
        return []

    try:
        fetch_handle = Entrez.efetch(
            db="pubmed",
            id=",".join(ids),
            rettype="abstract",
            retmode="xml",
        )
        xml_data = fetch_handle.read()
        root = ElementTree.fromstring(xml_data)
    except Exception as error:
        logger.warning("Error fetching PubMed records: %s", error)
        return []

    candidates = []

    for article in root.findall(".//PubmedArticle"):
        title = "".join(article.find(".//ArticleTitle").itertext()).strip() if article.find(".//ArticleTitle") is not None else ""
        abstract = _extract_abstract(article)
        if not title or not abstract:
            continue

        pmid = article.findtext(".//PMID")
        published = _extract_publication_date(article)
        if not pmid:
            continue

        candidates.append({
            "title": title,
            "abstract": abstract,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "source": "pubmed",
            "published": published.isoformat(),
            "_published_datetime": published,
        })

    if not candidates:
        return []

    reference_date = max(paper["_published_datetime"] for paper in candidates)
    cutoff = reference_date - timedelta(days=days_back)

    papers = []
    for paper in candidates:
        if paper["_published_datetime"] >= cutoff:
            cleaned = dict(paper)
            del cleaned["_published_datetime"]
            papers.append(cleaned)

    return papers
