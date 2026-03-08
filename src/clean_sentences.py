import re


def clean_sentence(s):

    s = s.strip()

    s = re.sub(r"^(Introduction|Conclusion|Results|Methods)\s+", "", s)
    s = s.replace("- ", "")

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

    # remove very short sentences
    if len(s) < 80:
        return None
    
    # remove sentences that look like references
    if is_reference(s):
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