from datetime import datetime
import html
import logging
import re

import feedparser
import requests
from triage.taxonomy import COARSE_CHEMISTRY_TERMS, keyword_match
from sources.dates import PublicationWindow, parse_publication_date
from sources.outcomes import SourceResult, eligible_result, error_diagnostic
from collections import Counter


CHEMRXIV_RSS = "https://chemrxiv.org/engage/chemrxiv/rss"
CAMBRIDGE_COE_RSS = "https://www.cambridge.org/engage/rss/coe"
CROSSREF_API_URL = "https://api.crossref.org/works"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0 Safari/537.36"
    )
}

SPARSE_CROSSREF_TERMS = (
    "docking",
    "virtual screening",
    "binding affinity",
    "protein-ligand",
    "ligand design",
    "lead optimization",
    "admet",
    "qsar",
    "cheminformatics",
    "drug discovery",
    "molecular design",
    "molecular generation",
    "molecular dynamics",
    "free energy",
)
logger = logging.getLogger(__name__)

def _strip_html(text):
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _make_session():
    session = requests.Session()
    session.trust_env = False
    session.headers.update(REQUEST_HEADERS)
    return session


def _fetch_feed_xml(url):
    session = _make_session()
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def _fetch_crossref_items(days_back, rows=200, *, reference_time=None):
    session = _make_session()
    window = PublicationWindow.recent(days_back, reference_time)
    today = window.end.date().isoformat()
    from_date = window.start.date().isoformat()
    params = {
        "filter": f"from-pub-date:{from_date},until-pub-date:{today},prefix:10.26434",
        "rows": rows,
    }
    headers = {
        "User-Agent": "ai-drug-discovery-digest/1.0 (mailto:chemrxiv-fetch@example.com)"
    }
    response = session.get(CROSSREF_API_URL, params=params, timeout=30, headers=headers)
    response.raise_for_status()
    payload = response.json()
    return payload["message"]["items"]


def _is_block_page(feed_text):
    lowered = (feed_text or "").lower()
    return "enable javascript and cookies to continue" in lowered or "just a moment" in lowered


def _entry_value(entry, key):
    if isinstance(entry, dict):
        # Bypass feedparser's compatibility alias from updated to published.
        return dict.get(entry, key)
    getter = getattr(entry, "get", None)
    return getter(key) if getter else getattr(entry, key, None)


def _extract_datetime(entry):
    # An update is never a substitute for publication.
    return parse_publication_date(_entry_value(entry, "published"))[0]


def _looks_like_chemrxiv_entry(entry):
    getter = getattr(entry, "get", None)
    link = ((getter("link") if getter else getattr(entry, "link", "")) or "").lower()
    title = (getter("title") if getter else getattr(entry, "title", "")) or ""
    summary = (getter("summary") if getter else getattr(entry, "summary", "")) or ""
    text = f"{title} {summary}".lower()

    if "chemrxiv" in link or "10.26434" in link:
        return True

    chemistry_hits = sum(term in text for term in COARSE_CHEMISTRY_TERMS)
    return chemistry_hits >= 2 and keyword_match(text)


def _matches_crossref_target_domain(title, abstract):
    title = (title or "").strip()
    abstract = _strip_html(abstract or "")
    text = f"{title} {abstract}".strip()

    if keyword_match(text):
        return True

    if not title:
        return False

    # Crossref often only gives us a title, so allow a slightly looser gate here.
    if abstract and abstract.lower() != title.lower():
        return False

    lowered_title = title.lower()
    direct_hits = sum(term in lowered_title for term in SPARSE_CROSSREF_TERMS)
    chemistry_hits = sum(term in lowered_title for term in COARSE_CHEMISTRY_TERMS)
    return direct_hits >= 1 and (chemistry_hits >= 1 or "benchmark" in lowered_title)


def _parse_feed_entries(feed_text, days_back, chemrxiv_only=False, *, reference_time=None):
    feed = feedparser.parse(feed_text)
    entries = list(getattr(feed, "entries", []))
    if not getattr(feed, "version", ""):
        raise ValueError("Invalid feed")
    errors = ([error_diagnostic("chemrxiv.feed_parse", getattr(feed, "bozo_exception", ValueError()))]
              if getattr(feed, "bozo", False) else [])
    window = PublicationWindow.recent(days_back, reference_time)
    papers = []

    for entry in entries:
        getter = getattr(entry, "get", None)
        title = _strip_html((getter("title") if getter else getattr(entry, "title", "")) or "")
        summary = _strip_html((getter("summary") if getter else getattr(entry, "summary", "")) or "")
        link = (getter("link") if getter else getattr(entry, "link", "")) or ""

        if not title or not summary or not link:
            continue

        if chemrxiv_only and not _looks_like_chemrxiv_entry(entry):
            continue

        if not keyword_match(f"{title} {summary}"):
            continue

        papers.append({
            "title": title,
            "abstract": summary,
            "url": link,
            "source": "chemrxiv",
            "published": _entry_value(entry, "published") or "",
            "updated": _entry_value(entry, "updated") or "",
        })

    return eligible_result(papers, window, source="chemrxiv", errors=errors, completed=not errors)


def _date_from_parts(parts):
    if len(parts) != 3:
        return None
    try:
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return datetime(year, month, day)
    except Exception:
        return None


def _parse_crossref_entries(days_back, *, reference_time=None):
    window = PublicationWindow.recent(days_back, reference_time)
    items = _fetch_crossref_items(days_back, reference_time=window.end)
    papers = []

    for item in items:
        title = " ".join(item.get("title") or []).strip()
        if not title:
            continue

        published_parts = ((item.get("published") or {}).get("date-parts") or [[]])[0]
        published = _date_from_parts(published_parts)

        abstract = _strip_html(item.get("abstract") or "")
        if not abstract:
            abstract = title

        if not _matches_crossref_target_domain(title, abstract):
            continue

        resource_url = (
            ((item.get("resource") or {}).get("primary") or {}).get("URL")
            or item.get("URL")
            or ""
        )
        if not resource_url:
            continue

        papers.append({
            "title": title,
            "abstract": abstract,
            "url": resource_url,
            "source": "chemrxiv",
            "published": published.date().isoformat() if published else (str(published_parts) if published_parts else ""),
            "publication_date_original": item.get("published"),
            "posted_original": item.get("posted"),
        })

    return eligible_result(papers, window, source="chemrxiv")


def fetch_chemrxiv_papers(days_back=14, *, reference_time=None):
    window = PublicationWindow.recent(days_back, reference_time)
    errors, rejected = [], Counter()
    completed = False
    routes = [
        ("chemrxiv.rss", lambda: _parse_feed_entries(_fetch_feed_xml(CHEMRXIV_RSS), days_back, reference_time=window.end)),
        ("chemrxiv.crossref", lambda: _parse_crossref_entries(days_back, reference_time=window.end)),
        ("chemrxiv.cambridge", lambda: _parse_feed_entries(_fetch_feed_xml(CAMBRIDGE_COE_RSS), days_back, chemrxiv_only=True, reference_time=window.end)),
    ]
    for stage, fetch in routes:
        try:
            papers = fetch()
            completed = completed or papers.completed
            errors.extend(papers.errors)
            rejected.update(papers.date_rejections)
            if papers:
                return SourceResult(papers, source="chemrxiv", errors=errors, completed=papers.completed, date_rejections=rejected)
        except Exception as error:
            errors.append(error_diagnostic(stage, error))
    return SourceResult(source="chemrxiv", errors=errors, completed=completed, date_rejections=rejected)


if __name__ == "__main__":
    papers = fetch_chemrxiv_papers()
    print(f"Fetched {len(papers)} ChemRxiv papers")
    for paper in papers[:5]:
        print("-", paper["title"])
