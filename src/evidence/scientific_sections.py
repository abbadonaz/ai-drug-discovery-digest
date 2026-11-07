"""Conservative line-anchored headings and traceable evidence passages."""
import hashlib
import re


HEADINGS = {
    "abstract": "abstract", "introduction": "introduction", "background": "introduction",
    "introduction and background": "introduction", "methods": "methods", "methodology": "methods",
    "materials and methods": "methods", "experimental methods": "methods",
    "experimental setup": "experimental_setup", "experimental design": "experimental_setup",
    "datasets": "datasets", "data sets": "datasets", "data": "datasets",
    "model architecture": "model_architecture", "training and validation": "training_validation",
    "training": "training_validation", "evaluation protocol": "training_validation",
    "results": "results", "results and discussion": "results_discussion",
    "discussion": "discussion", "limitations": "limitations", "limitations and future work": "limitations",
    "conclusion": "conclusion", "conclusions": "conclusion",
    "supplementary information": "supplementary", "supporting information": "supplementary",
    "references": "references", "bibliography": "references",
}
METHOD_CATEGORIES = {"methods", "experimental_setup", "datasets", "model_architecture", "training_validation"}


def heading(line):
    cleaned = re.sub(r"^(?:\d+(?:\.\d+)*\.?|[IVX]+\.)\s+", "", line.strip())
    cleaned = cleaned.rstrip(":").lower().replace(" & ", " and ")
    return HEADINGS.get(cleaned)


def detect_sections(document: dict) -> list[dict]:
    text = document["text"]
    lines, offset = [], 0
    for line in text.splitlines(keepends=True):
        lines.append((offset, line.strip(), len(line)))
        offset += len(line)
    starts, index, inherited = [], 0, "unknown"
    while index < len(lines):
        start, title, length = lines[index]
        category = heading(title)
        consumed = 1
        # A heading split across lines is recognized only if the combined title
        # exactly matches a known heading, never from prose keywords.
        if title and index + 1 < len(lines) and lines[index + 1][1]:
            combined = title + " " + lines[index + 1][1]
            if heading(combined):
                category, title, consumed = heading(combined), combined, 2
        status = "exact_heading"
        if not category and re.fullmatch(r"\d+(?:\.\d+)+\s+[A-Z][A-Za-z /-]{2,55}", title):
            category, status = inherited, "inherited_numbered_subsection"
        if category:
            end = lines[index + consumed - 1][0] + lines[index + consumed - 1][2]
            starts.append((start, end, title, category, status))
            inherited = category
        index += consumed
    if not starts or starts[0][0] > 0:
        starts.insert(0, (0, 0, "Unknown", "unknown", "unknown"))
    blocks = [b for p in document["pages"] for b in p["blocks"] if b["start"] is not None]
    sections = []
    for i, (start, content_start, title, category, status) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        pages = [b["page"] for b in blocks if b["end"] > start and b["start"] < end]
        sections.append({"title": title, "category": category, "start": start, "content_start": content_start,
                         "end": end, "page_start": min(pages) if pages else None,
                         "page_end": max(pages) if pages else None, "detection": status,
                         "text": text[content_start:end]})
    return sections


def passage_id(paper_id, source_type, start, end, text):
    material = f"{paper_id}\0{source_type}\0{start}\0{end}\0{text}"
    return "P" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def build_passages(document: dict, paper_id: str) -> list[dict]:
    sections = detect_sections(document)
    passages = []
    for section in sections:
        for page in document["pages"]:
            for block in page["blocks"]:
                if block["start"] is None:
                    continue
                start, end = max(section["content_start"], block["start"]), min(section["end"], block["end"])
                raw_span = document["text"][start:end] if start < end else ""
                text = re.sub(r"\s+", " ", raw_span).strip()
                if not text:
                    continue
                table = re.search(r"\bTable\s+(\d+[A-Za-z]?)\b", text, re.I)
                numeric_fragment = len(re.findall(r"\d+(?:\.\d+)?", text)) >= 4 and sum(c.isalpha() for c in text) < 35
                passages.append({"passage_id": passage_id(paper_id, "pdf", start, end, text),
                                 "paper_id": paper_id, "source_type": "pdf", "section_title": section["title"],
                                 "section": section["category"], "section_detection": section["detection"],
                                 "page_start": page["page"], "page_end": page["page"], "block_id": block["block_id"],
                                 "start": start, "end": end, "text": text, "source_text": raw_span,
                                 "table_id": table.group(0) if table else None,
                                 "extraction_status": document["status"],
                                 "limitations": [*document["limitations"], *(["ambiguous_numeric_block"] if numeric_fragment else [])],
                                 "support_status": "unverified"})
    return passages


def abstract_passages(paper: dict) -> list[dict]:
    text = paper.get("abstract") or (paper.get("sections") or {}).get("abstract", "")
    paper_id = paper.get("url", paper.get("title", "unknown"))
    passages = []
    # Keep sentence-level abstract fallback without assigning PDF pages.
    for match in re.finditer(r".+?(?:[.!?](?=\s|$)|$)", text):
        value = match.group().strip()
        if value:
            passages.append({"passage_id": passage_id(paper_id, "abstract", match.start(), match.end(), value),
                             "paper_id": paper_id, "source_type": "abstract", "section_title": "Source abstract",
                             "section": "abstract", "section_detection": "source_metadata", "page_start": None,
                             "page_end": None, "start": match.start(), "end": match.end(), "text": value,
                             "extraction_status": "abstract_only", "limitations": ["abstract_only"],
                             "support_status": "unverified"})
    return passages
