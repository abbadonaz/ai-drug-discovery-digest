import re


SECTION_PATTERNS = {
    "abstract": r"\babstract\b",
    "introduction": r"\bintroduction\b",
    "methods": r"\bmethods?\b",
    "results": r"\bresults?\b",
    "discussion": r"\bdiscussion\b",
    "conclusion": r"\bconclusion\b",
}


def extract_sections(text):

    sections = {}

    lower = text.lower()

    for name, pattern in SECTION_PATTERNS.items():

        match = re.search(pattern, lower)

        if match:

            start = match.start()

            snippet = text[start:start + 6000]

            sections[name] = snippet

    return sections

def build_paper_context(sections):

    important = []

    for key in ["abstract", "introduction", "results", "conclusion"]:

        if key in sections:
            important.append(sections[key])

    return "\n".join(important)