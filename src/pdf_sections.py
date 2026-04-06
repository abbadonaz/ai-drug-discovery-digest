import re

from config import MAX_SECTION_CHARS


SECTION_PATTERNS = {
    "abstract": r"\babstract\b",
    "introduction": r"\bintroduction\b",
    "methods": r"\bmethods?\b",
    "results": r"\bresults?\b",
    "discussion": r"\bdiscussion\b",
    "conclusion": r"\bconclusion\b",
}


def extract_sections(text):
    if not text:
        return {}

    lower = text.lower()
    matches = []

    for name, pattern in SECTION_PATTERNS.items():
        match = re.search(pattern, lower)
        if match:
            matches.append((match.start(), name))

    matches.sort()
    sections = {}

    for index, (start, name) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        snippet = text[start:end].strip()
        if snippet:
            sections[name] = snippet[:MAX_SECTION_CHARS]

    return sections


def build_paper_context(sections):
    important = []

    for key in ["abstract", "introduction", "results", "discussion", "conclusion"]:
        section_text = (sections or {}).get(key)
        if section_text:
            important.append(section_text)

    return "\n\n".join(important)
