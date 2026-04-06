from pathlib import Path
from urllib.parse import urlparse

import requests


PDF_DIR = Path("data/pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_HEADERS = {
    "User-Agent": "ai-drug-discovery-digest/1.0 (+https://github.com/abbadonaz)"
}


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
        if "pdf" not in content_type and not pdf_url.lower().endswith(".pdf"):
            return None

        with path.open("wb") as f:
            f.write(response.content)

        return path
    except Exception:
        return None
