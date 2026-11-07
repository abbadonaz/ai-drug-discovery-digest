import os
import logging
from datetime import datetime, timezone
from xml.etree import ElementTree

from Bio import Entrez
from triage.taxonomy import build_pubmed_query
from sources.dates import PublicationWindow
from sources.outcomes import SourceResult, eligible_result, error_diagnostic


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
    month = article.findtext(".//PubDate/Month", "")
    day = article.findtext(".//PubDate/Day", "")

    month_lookup = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    try:
        month_value = int(month)
    except ValueError:
        month_value = month_lookup.get(month.lower(), 0)

    try:
        return datetime(int(year), int(month_value), int(day), tzinfo=timezone.utc)
    except Exception:
        return None


def fetch_pubmed_papers(days_back=14, max_results=200, *, reference_time=None):
    window = PublicationWindow.recent(days_back, reference_time)
    try:
        handle = Entrez.esearch(
            db="pubmed",
            term=QUERY,
            retmax=max_results,
            sort="pub date",
        )
        record = Entrez.read(handle)
        ids = record["IdList"]
    except Exception as error:
        return SourceResult(source="pubmed", completed=False, errors=[error_diagnostic("pubmed.search", error)])

    if not ids:
        return SourceResult(source="pubmed")

    try:
        fetch_handle = Entrez.efetch(
            db="pubmed",
            id=",".join(ids),
            rettype="abstract",
            retmode="xml",
        )
        xml_data = fetch_handle.read()
        root = ElementTree.fromstring(xml_data)
        if root.tag != "PubmedArticleSet":
            raise ValueError("Invalid PubMed response")
    except Exception as error:
        return SourceResult(source="pubmed", completed=False, errors=[error_diagnostic("pubmed.fetch", error)])

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
            "published": published.date().isoformat() if published else (
                article.findtext(".//PubDate/MedlineDate") or
                " ".join(article.findtext(f".//PubDate/{key}", "") for key in ("Year", "Month", "Day")).strip()
            ),
            "publication_date_original": {key: article.findtext(f".//PubDate/{key}") for key in ("Year", "Month", "Day", "MedlineDate")},
            "updated_original": {key: article.findtext(f".//DateRevised/{key}") for key in ("Year", "Month", "Day")},
        })

    returned_ids = {node.text for node in root.findall(".//PubmedArticle//PMID")}
    complete = set(ids).issubset(returned_ids)
    errors = [] if complete else [{"stage": "pubmed.fetch", "error_type": "IncompleteResponse"}]
    return eligible_result(candidates, window, source="pubmed", errors=errors, completed=complete)
