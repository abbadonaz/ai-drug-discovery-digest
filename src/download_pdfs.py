import requests
from pathlib import Path


PDF_DIR = Path("data/pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)


def get_pdf_filename(paper):

    url = paper.get("pdf_url") or paper.get("url")

    paper_id = url.split("/")[-1].replace(".pdf", "")

    return PDF_DIR / f"{paper_id}.pdf"


def download_pdf(paper):

    pdf_url = paper.get("pdf_url")

    if not pdf_url:
        return None

    path = get_pdf_filename(paper)

    if path.exists():
        return path

    try:

        r = requests.get(pdf_url, timeout=30)
        r.raise_for_status()

        with open(path, "wb") as f:
            f.write(r.content)

        return path

    except Exception:

        return None