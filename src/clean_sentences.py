import re


SECTION_PREFIX_RE = re.compile(
    r"^(Abstract|Introduction|Conclusion|Results|Methods|Background|Objective|Objectives|Purpose|Aim|Aims|Discussion)\s*[:\-]?\s+",
    re.IGNORECASE,
)
NUMBERED_SECTION_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*\s+)+(Abstract|Introduction|Conclusion|Results|Methods|Background|Objective|Objectives|Purpose|Aim|Aims|Discussion)\s*[:\-]?\s+",
    re.IGNORECASE,
)
SUBSECTION_HEADER_RE = re.compile(
    r"^\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9\-]+(?:\s+[A-Z][A-Za-z0-9\-]+){0,8}:\s+"
)
TRAILING_FRAGMENT_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "using",
    "via",
    "was",
    "were",
    "which",
    "with",
}


def _alphabetic_ratio(text):
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return 0.0
    alpha = sum(char.isalpha() for char in compact)
    return alpha / len(compact)


def _looks_like_table_artifact(text):
    compact = re.sub(r"\s+", "", text or "")
    digits = sum(char.isdigit() for char in compact)
    alpha = sum(char.isalpha() for char in compact)
    symbols = sum(char in "+-=|†‡§±/%<>" for char in compact)
    numeric_groups = re.findall(r"[+\-]?\d+(?:\.\d+)?", text or "")

    if symbols >= 8 and digits >= 6 and alpha < digits * 2:
        return True

    if len(numeric_groups) >= 6 and alpha < 40:
        return True

    if (text or "").count("†") + (text or "").count("‡") >= 2 and digits >= 4:
        return True

    if _alphabetic_ratio(text) < 0.55 and digits >= 6:
        return True

    return False


def _looks_incomplete(text):
    stripped = (text or "").strip()
    if not stripped:
        return True

    if stripped.count("(") > stripped.count(")"):
        return True

    if stripped.count("[") > stripped.count("]"):
        return True

    if re.search(r"[.!?][\"')\]]?$", stripped):
        return False

    words = re.findall(r"[A-Za-z]+", stripped)
    if words and words[-1].lower() in TRAILING_FRAGMENT_WORDS:
        return True

    return len(stripped) > 140


def clean_sentence(s):

    s = s.strip()

    s = NUMBERED_SECTION_RE.sub("", s)
    s = SECTION_PREFIX_RE.sub("", s)
    s = SUBSECTION_HEADER_RE.sub("", s)
    s = s.replace("- ", "")

    if s.startswith("(") and re.search(r"\b(results?|methods?|discussion|conclusion)\b", s, flags=re.IGNORECASE):
        return None

    if s.endswith(("t", "exp", "res", "demonstrating")):
        return None

    # remove figure references
    s = re.sub(r"\(Fig\.[^)]+\)", "", s)

    # remove citation brackets
    s = re.sub(r"\[[0-9, ]+\]", "", s)

    # remove keywords section
    if s.lower().startswith("keywords"):
        return None

    # remove sentences that are mostly numbers
    if re.fullmatch(r"[0-9\s\.\-]+", s):
        return None

    if _looks_like_table_artifact(s):
        return None

    # remove very short sentences
    if len(s) < 80:
        return None

    # remove sentences that look like references
    if is_reference(s):
        return None

    if _looks_incomplete(s):
        return None

    return s


def deduplicate(sentences):

    seen = set()
    clean = []

    for s in sentences:

        s = s.strip()

        if s not in seen:
            seen.add(s)
            clean.append(s)

    return clean


def clean_sentences(sentences):

    cleaned = []

    for s in sentences:

        s = clean_sentence(s)

        if s:
            cleaned.append(s)

    cleaned = deduplicate(cleaned)

    return cleaned

def is_reference(sentence):

    # typical reference patterns
    if "et al." in sentence:
        return True

    if ":" in sentence and "," in sentence and len(sentence) < 120:
        return True

    if "doi" in sentence.lower():
        return True

    if "arxiv" in sentence.lower():
        return True

    return False
