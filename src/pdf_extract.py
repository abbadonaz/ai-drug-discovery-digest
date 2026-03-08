from pdfminer.high_level import extract_text    
import re


from pdfminer.high_level import extract_text
import re


def clean_text(text):
    """
    Remove common PDF artifacts like page numbers,
    broken lines and reference numbering.
    """

    # remove page numbers
    text = re.sub(r'\n\d+\n', '\n', text)

    # remove multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # remove section numbering like "1 INTRODUCTION"
    text = re.sub(r'\b\d+\s+[A-Z]{3,}\b', '', text)

    # remove strange number blocks
    text = re.sub(r'(\d+\s+){4,}', '', text)

    return text.strip()


def extract_pdf_text(pdf_path):

    try:

        raw = extract_text(pdf_path)

        clean = clean_text(raw)

        return clean

    except Exception:

        return ""


def split_sentences(text):

    sentences = re.split(r'(?<=[.!?])\s+', text)

    sentences = [
        s.strip()
        for s in sentences
        if len(s) > 80 and len(s) < 400
    ]

    return sentences