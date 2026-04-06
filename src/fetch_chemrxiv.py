from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import html
import re

import feedparser
import requests


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

KEYWORDS = [
    "drug discovery",
    "computational chemistry",
    "molecular docking",
    "docking",
    "virtual screening",
    "ligand",
    "protein-ligand",
    "binding affinity",
    "qsar",
    "admet",
    "cheminformatics",
    "molecular design",
    "molecular generation",
    "molecular dynamics",
    "quantum chemistry",
    "active learning",
    "bayesian optimization",
    "fep",
    "free energy perturbation",
    "uncertainty quantification",
]

COARSE_CHEMISTRY_TERMS = [
    "chemistry",
    "molecule",
    "molecular",
    "docking",
    "ligand",
    "protein",
    "screening",
    "synthesis",
    "reaction",
    "compound",
]


def keyword_match(text):
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in KEYWORDS)


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


def _fetch_crossref_items(days_back, rows=200):
    session = _make_session()
    today = datetime.utcnow().date().isoformat()
    from_date = (datetime.utcnow() - timedelta(days=days_back)).date().isoformat()
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
    return payload.get("message", {}).get("items", [])


def _is_block_page(feed_text):
    lowered = (feed_text or "").lower()
    return "enable javascript and cookies to continue" in lowered or "just a moment" in lowered


def _extract_datetime(entry):
    published = getattr(entry, "get", lambda key, default=None: default)("published")
    if not published:
        published = getattr(entry, "get", lambda key, default=None: default)("updated")
    if not published:
        published = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not published:
        return None

    try:
        parsed = parsedate_to_datetime(published)
        if parsed.tzinfo is None:
            return parsed
        return parsed.replace(tzinfo=None)
    except Exception:
        return None


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


def _parse_feed_entries(feed_text, days_back, chemrxiv_only=False):
    feed = feedparser.parse(feed_text)
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    papers = []

    for entry in getattr(feed, "entries", []):
        published = _extract_datetime(entry)
        if published and published < cutoff:
            continue

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
            "published": (published or datetime.utcnow()).isoformat(),
        })

    return papers


def _date_from_parts(parts):
    if not parts:
        return None
    try:
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return datetime(year, month, day)
    except Exception:
        return None


def _parse_crossref_entries(days_back):
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    papers = []

    for item in _fetch_crossref_items(days_back):
        title = " ".join(item.get("title") or []).strip()
        if not title:
            continue

        published_parts = ((item.get("published") or {}).get("date-parts") or [[]])[0]
        posted_parts = ((item.get("posted") or {}).get("date-parts") or [[]])[0]
        published = _date_from_parts(published_parts) or _date_from_parts(posted_parts) or datetime.utcnow()
        if published < cutoff:
            continue

        abstract = _strip_html(item.get("abstract") or "")
        if not abstract:
            abstract = title

        text = f"{title} {abstract}"
        if not keyword_match(text):
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
            "published": published.isoformat(),
        })

    return papers


def fetch_chemrxiv_papers(days_back=14):
    try:
        feed_text = _fetch_feed_xml(CHEMRXIV_RSS)
        if _is_block_page(feed_text):
            raise RuntimeError("ChemRxiv RSS is blocked by a challenge page")

        papers = _parse_feed_entries(feed_text, days_back, chemrxiv_only=False)
        if papers:
            return papers
    except Exception as error:
        print(f"ChemRxiv RSS fetch failed: {error}")

    try:
        papers = _parse_crossref_entries(days_back)
        if papers:
            print(f"ChemRxiv fallback activated via Crossref: {len(papers)} candidate papers")
            return papers
        print("ChemRxiv Crossref fallback reachable, but no target-domain preprints matched the keyword filter.")
    except Exception as error:
        print(f"ChemRxiv Crossref fallback failed: {error}")

    try:
        fallback_text = _fetch_feed_xml(CAMBRIDGE_COE_RSS)
        papers = _parse_feed_entries(fallback_text, days_back, chemrxiv_only=True)
        if papers:
            print(f"ChemRxiv fallback activated via Cambridge Open Engage feed: {len(papers)} candidate papers")
        else:
            print("ChemRxiv fallback feed reachable, but no ChemRxiv-like entries matched the target domains.")
        return papers
    except Exception as error:
        print(f"ChemRxiv fallback fetch failed: {error}")
        return []


if __name__ == "__main__":
    papers = fetch_chemrxiv_papers()
    print(f"Fetched {len(papers)} ChemRxiv papers")
    for paper in papers[:5]:
        print("-", paper["title"])
