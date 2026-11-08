"""Conservative line-anchored headings and traceable evidence passages."""
import hashlib
import re
from digest_core.config import EVIDENCE_PASSAGE_MAX_CHARS


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
    "discussion and limitations": "limitations", "experiments": "experimental_setup",
    "conclusion": "conclusion", "conclusions": "conclusion",
    "supplementary information": "supplementary", "supporting information": "supplementary",
    "references": "references", "bibliography": "references",
}
METHOD_CATEGORIES = {"methods", "experimental_setup", "datasets", "model_architecture", "training_validation"}


def extract_document_abstract(document: dict) -> str:
    """Keep available abstract prose in its column; budgeting happens at selection."""
    pages = document.get("pages", [])
    for page_index, page in enumerate(pages[:2]):
        blocks = [b for b in page["blocks"] if b["text"].strip() and not b.get("excluded_margin")]
        for block in blocks:
            match = re.match(r"^Abstract(?:\s*[—–:-]\s*|\s*$)", block["text"], re.I)
            if match is None:
                continue
            center = (block["bbox"][0] + block["bbox"][2]) / 2
            content = [block["text"][match.end():]] if block["text"][match.end():].strip() else []
            mid = page["width"] / 2
            column = sorted((b for b in blocks if b is not block and (b["bbox"][0] <= center <= b["bbox"][2]
                             or (heading(b["text"].splitlines()[0]) and ((b["bbox"][0] + b["bbox"][2]) / 2 < mid) == (center < mid)))
                             and b["bbox"][3] <= block["bbox"][3]), key=lambda b: -b["bbox"][3])
            for candidate in column:
                first = candidate["text"].splitlines()[0].strip() if candidate["text"] else ""
                if heading(first) or re.match(r"^(?:\d+\s+)?(?:Introduction|Impact Statement|Index Terms|Keywords)\b", first, re.I):
                    break
                if candidate["text"].strip():
                    if re.fullmatch(r"[\d\s]+", candidate["text"]):
                        continue
                    content.append(candidate["text"])
            else:
                # An abstract may continue onto the next page; stop at its
                # first real heading/keyword label rather than silently cut it.
                if page_index + 1 < len(pages):
                    following = sorted(pages[page_index + 1]["blocks"], key=lambda b: -b["bbox"][3])
                    for candidate in following:
                        if candidate.get("excluded_margin") or not candidate["text"].strip():
                            continue
                        first = candidate["text"].splitlines()[0].strip()
                        if heading(first) or re.match(r"^(?:Keywords|Index Terms)\b", first, re.I):
                            break
                        if candidate["bbox"][0] <= center <= candidate["bbox"][2] and not re.fullmatch(r"[\d\s]+", candidate["text"]):
                            content.append(candidate["text"])
            return re.sub(r"\s+", " ", " ".join(content)).strip()
    return ""


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


def sentence_spans(text: str, start: int, end: int, max_chars: int) -> list[tuple[int, int]]:
    """Split oversized prose at sentence ends, never cut a value or a sentence."""
    boundaries = [start + m.end() for m in re.finditer(r"[.!?](?=\s+[A-Z]|\s*$)", text[start:end])]
    spans, cursor = [], start
    while end - cursor > max_chars:
        fitting = [b for b in boundaries if cursor < b <= cursor + max_chars]
        boundary = max(fitting) if fitting else next((b for b in boundaries if b > cursor), end)
        spans.append((cursor, boundary))
        cursor = boundary
    if cursor < end:
        spans.append((cursor, end))
    return spans


def build_passages(document: dict, paper_id: str, max_chars: int = EVIDENCE_PASSAGE_MAX_CHARS) -> list[dict]:
    if max_chars < 1:
        raise ValueError("Passage character budget must be positive")
    sections = detect_sections(document)
    passages = []
    for section in sections:
        for page in document["pages"]:
            for block in page["blocks"]:
                if block["start"] is None:
                    continue
                start, end = max(section["content_start"], block["start"]), min(section["end"], block["end"])
                category = section["category"]
                span_text = re.sub(r"\s+", " ", document["text"][start:end]).strip() if start < end else ""
                if category != "references":
                    if re.match(r"^Abstract[—–:-]", span_text, re.I):
                        category = "abstract"
                    elif re.match(r"^Limitations[.:]\s", span_text, re.I) or re.search(
                        r"\bour (?:study|work) has (?:substantial )?room for improvement\b", span_text, re.I
                    ):
                        category = "limitations"
                    elif re.match(r"^Results[.:]\s", span_text, re.I):
                        category = "results"
                for start, end in sentence_spans(document["text"], start, end, max_chars) if start < end else []:
                    raw_span = document["text"][start:end]
                    text = re.sub(r"\s+", " ", raw_span).strip()
                    if not text:
                        continue
                    table = re.search(r"\bTable\s+(\d+[A-Za-z]?)\b", text, re.I)
                    numeric_fragment = len(re.findall(r"\d+(?:\.\d+)?", text)) >= 4 and sum(c.isalpha() for c in text) < 35
                    passages.append({"passage_id": passage_id(paper_id, "pdf", start, end, text),
                                 "paper_id": paper_id, "source_type": "pdf", "section_title": section["title"],
                                 "section": category, "section_detection": "run_in_label" if category != section["category"] else section["detection"],
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
