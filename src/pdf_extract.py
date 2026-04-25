import re

try:
    from pdfminer.high_level import extract_text
except Exception:  # pragma: no cover - dependency availability depends on local setup
    extract_text = None


def clean_text(text):
    """
    Remove common PDF artifacts like page numbers,
    broken lines and reference numbering.
    """

    text = re.sub(r"\n\d+\n", "\n", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b\d+\s+[A-Z]{3,}\b", "", text)
    text = re.sub(r"(\d+\s+){4,}", "", text)
    return text.strip()


def extract_pdf_text(pdf_path):
    if extract_text is None:
        return ""

    try:
        raw = extract_text(pdf_path)
        return clean_text(raw)
    except Exception:
        return ""


def split_sentences(text):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [
        sentence.strip()
        for sentence in sentences
        if len(sentence) > 80 and len(sentence) < 400
    ]
