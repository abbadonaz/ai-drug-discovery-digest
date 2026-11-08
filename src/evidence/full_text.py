"""Bounded public-source PDF retrieval with explicit outcomes and cache identity."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit
from xml.etree import ElementTree as ET

import requests

from digest_core.atomic import stage_bytes
from digest_core.config import MAX_PDF_BYTES
from digest_core.utils import save_json


HOSTS = {"arxiv.org", "export.arxiv.org", "www.arxiv.org", "chemrxiv.org", "www.chemrxiv.org",
         "www.cambridge.org", "eutils.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov",
         "pmc.ncbi.nlm.nih.gov", "pmc-oa-opendata.s3.amazonaws.com"}


def validate_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or parsed.hostname not in HOSTS or parsed.username
            or parsed.password or parsed.port not in (None, 80, 443) or any(ord(c) < 33 for c in url)):
        raise ValueError("unsafe_or_unsupported_url")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("nonpublic_address")


def fetch_bytes(url, limit, session=None):
    owned = session is None
    session = session or requests.Session()
    session.trust_env = False
    try:
        for _ in range(5):
            validate_url(url)
            with session.get(url, stream=True, allow_redirects=False, timeout=(10, 45),
                             headers={"User-Agent": "ai-drug-discovery-digest/1.0"}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers["Location"])
                    continue
                response.raise_for_status()
                if int(response.headers.get("Content-Length", "0")) > limit:
                    raise ValueError("download_limit")
                parts, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > limit:
                        raise ValueError("download_limit")
                    parts.append(chunk)
                return b"".join(parts), url
        raise ValueError("redirect_limit")
    finally:
        if owned:
            session.close()


def pdf_routes(paper):
    routes = [paper["pdf_url"]] if paper.get("pdf_url") else []
    parsed = urlsplit(paper.get("url", ""))
    if parsed.hostname in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
        identifier = re.fullmatch(r"/(?:abs|pdf)/([A-Za-z0-9./-]+?)(?:\.pdf)?", parsed.path)
        if identifier:
            routes.append("https://arxiv.org/pdf/" + identifier.group(1))
    if parsed.hostname in {"chemrxiv.org", "www.chemrxiv.org"} and parsed.path.startswith("/doi/full/"):
        routes.append("https://chemrxiv.org" + parsed.path.replace("/doi/full/", "/doi/pdf/", 1))
    return list(dict.fromkeys(routes))


class PDFMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name", "").lower() == "citation_pdf_url" and attrs.get("content"):
            self.urls.append(attrs["content"])


def pmc_routes(paper, fetch=fetch_bytes):
    pmcid = paper.get("pmcid", "")
    if not pmcid:
        match = re.search(r"/articles/(PMC\d+)", paper.get("url", ""))
        pmcid = match.group(1) if match else ""
    if not pmcid and urlsplit(paper.get("url", "")).hostname == "pubmed.ncbi.nlm.nih.gov":
        pmid = urlsplit(paper["url"]).path.strip("/")
        if pmid.isdigit():
            data, _ = fetch("https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?format=json&ids=" + pmid, 1_000_000)
            records = json.loads(data).get("records", [])
            pmcid = records[0].get("pmcid", "") if records else ""
    if not re.fullmatch(r"PMC\d+", pmcid):
        return []
    base = "https://pmc-oa-opendata.s3.amazonaws.com/"
    listing, _ = fetch(base + "?list-type=2&prefix=metadata/" + pmcid + ".&max-keys=100", 1_000_000)
    metadata = []
    for node in ET.fromstring(listing).iter():
        if node.tag.rsplit("}", 1)[-1] == "Key" and re.fullmatch(r"metadata/" + pmcid + r"\.\d+\.json", node.text or ""):
            raw, _ = fetch(base + quote(node.text, safe="/"), 1_000_000)
            record = json.loads(raw)
            if record.get("pdf_url") and record.get("license_code"):
                metadata.append(record)
    # Prefer an explicitly identified published article over a manuscript. Do
    # not assume a higher PMC version means a newer/preferred published article.
    metadata.sort(key=lambda m: (str(m.get("is_manuscript", "yes")).lower() != "no", str(m.get("version", ""))))
    return [m["pdf_url"] for m in metadata]


def retrieve_full_text(paper, cache_dir=Path("data/pdfs"), fetch=fetch_bytes):
    cache_dir = Path(cache_dir)
    identity = paper.get("url", "")
    key = hashlib.sha256(identity.encode()).hexdigest()
    target, sidecar = cache_dir / (key + ".pdf"), cache_dir / (key + ".json")
    result = {"outcome": "unavailable", "source_url": None, "document_id": None,
              "paper_id": identity, "path": None, "attempts": [], "reason": "no_public_pdf_route"}
    if target.exists() and target.stat().st_size <= MAX_PDF_BYTES and sidecar.exists():
        try:
            metadata, content = json.loads(sidecar.read_text(encoding="utf-8")), target.read_bytes()
            if metadata["paper_id"] == identity and metadata["document_id"] == hashlib.sha256(content).hexdigest() and content.startswith(b"%PDF-") and len(content) <= MAX_PDF_BYTES:
                return {**metadata, "outcome": "cached", "path": str(target), "reason": None}
        except (OSError, ValueError, KeyError):
            pass
    routes = pdf_routes(paper)
    if not routes and urlsplit(identity).hostname in {"chemrxiv.org", "www.chemrxiv.org"}:
        try:
            html, landing = fetch(identity, 1_000_000)
            parser = PDFMetadata()
            parser.feed(html.decode("utf-8", errors="replace"))
            routes.extend(urljoin(landing, url) for url in parser.urls)
        except Exception as error:
            result["attempts"].append({"stage": "chemrxiv_resolution", "error_type": type(error).__name__})
    # Reuse the pre-existing arXiv cache only for an exact versioned arXiv ID.
    match = re.fullmatch(r"/(?:abs|pdf)/(\d{4}\.\d{4,5}v\d+)(?:\.pdf)?", urlsplit(identity).path)
    if urlsplit(identity).hostname in {"arxiv.org", "www.arxiv.org"} and match:
        old = cache_dir / (match.group(1) + ".pdf")
        if old.exists() and old.stat().st_size <= MAX_PDF_BYTES:
            content = old.read_bytes()
            if content.startswith(b"%PDF-"):
                return {**result, "outcome": "cached", "source_url": routes[0] if routes else None,
                        "document_id": hashlib.sha256(content).hexdigest(), "path": str(old),
                        "reason": None, "cache_identity": "legacy_exact_arxiv_version"}
    try:
        routes += pmc_routes(paper, fetch)
    except Exception as error:
        result["attempts"].append({"stage": "pmc_resolution", "error_type": type(error).__name__})
    for url in dict.fromkeys(routes):
        try:
            content, final_url = fetch(url, MAX_PDF_BYTES)
            if not content.startswith(b"%PDF-") or len(content) > MAX_PDF_BYTES:
                raise ValueError("not_pdf")
            staged = stage_bytes(target, content)
            try:
                os.replace(staged, target)
            finally:
                staged.unlink(missing_ok=True)
            result.update(outcome="success", source_url=final_url, document_id=hashlib.sha256(content).hexdigest(), path=str(target), reason=None)
            save_json(result, sidecar)
            return result
        except Exception as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            reason = "access_denied" if status in (401, 403) else str(error) if isinstance(error, ValueError) else type(error).__name__
            result["attempts"].append({"stage": "pdf_download", "source_url": url.split("?")[0], "reason": reason, "http_status": status})
    if result["attempts"]:
        result.update(outcome="failed", reason=result["attempts"][-1].get("reason", "resolution_failed"))
    return result
