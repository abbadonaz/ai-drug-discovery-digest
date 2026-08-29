from pathlib import Path
from urllib.parse import urlparse

import requests
from digest_core.config import MAX_PDF_BYTES


PDF_DIR = Path("data/pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_HEADERS = {
    "User-Agent": "ai-drug-discovery-digest/1.0 (+https://github.com/abbadonaz)"
}
PDF_SIGNATURE = b"%PDF-"


def get_pdf_filename(paper):
    url = paper.get("pdf_url") or paper.get("url") or "paper"
    parsed = urlparse(url)
    candidate = Path(parsed.path).name or "paper"
    candidate = candidate.replace(".pdf", "") or "paper"
    safe_name = "".join(char if char.isalnum() or char in ("-", "_", ".") else "_" for char in candidate)
    return PDF_DIR / f"{safe_name}.pdf"


def download_pdf(paper):
    pdf_url = paper.get("pdf_url")
    if not pdf_url:
        return None

    path = get_pdf_filename(paper)
    if path.exists():
        return path

    try:
        response = requests.get(pdf_url, timeout=30, headers=REQUEST_HEADERS)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if not _looks_like_pdf_response(pdf_url, content_type):
            return None

        content = response.content
        if not _is_safe_pdf_content(content):
            return None

        with path.open("wb") as f:
            f.write(content)

        return path
    except Exception:
        return None


def _looks_like_pdf_response(url, content_type):
    return "pdf" in content_type or str(url).lower().endswith(".pdf")


def _is_safe_pdf_content(content):
    if not content or len(content) > MAX_PDF_BYTES:
        return False
    return content.lstrip()[:5] == PDF_SIGNATURE
