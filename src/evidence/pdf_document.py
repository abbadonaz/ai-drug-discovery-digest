"""Page/block-aware pdfminer adapter; no OCR or inferred table cells."""
from collections import Counter
import re

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextContainer


# Only known prose words are joined across visible line-end hyphens. Chemical
# names and arbitrary compounds keep their hyphen; original text stays available.
JOIN_WORDS = {"molecular", "prediction", "validation", "classification", "regression",
              "representation", "evaluation", "calibration", "experimental",
              "computational", "performance", "uncertainty", "optimization"}


def normalize_block(raw: str) -> str:
    def repair(match):
        left, right = match.group(1), match.group(2)
        return left + right if (left + right).lower() in JOIN_WORDS else left + "-" + right
    text = re.sub(r"([A-Za-z]+)-\s*\n\s*([a-z]+)", repair, raw)
    text = re.sub(r"\u00ad\s*\n\s*(?=[a-z])", "", text)
    # Keep line boundaries for heading detection. Paragraph joining happens only
    # after scientific sections have been located.
    return "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines()).strip()


def reading_order(blocks: list[dict], width: float) -> tuple[list[dict], str]:
    """Recognize simple two-column bands separated by full-width blocks."""
    mid = width / 2
    left = [b for b in blocks if b["bbox"][2] <= mid - width * .015]
    right = [b for b in blocks if b["bbox"][0] >= mid + width * .015]
    if not left or not right:
        return sorted(blocks, key=lambda b: (-b["bbox"][3], b["bbox"][0])), "single_or_unknown"
    # A visible gutter is necessary; overlapping boxes are not reconstructed.
    if max(b["bbox"][2] for b in left) >= min(b["bbox"][0] for b in right):
        return sorted(blocks, key=lambda b: (-b["bbox"][3], b["bbox"][0])), "ambiguous"
    spanning = sorted([b for b in blocks if b not in left and b not in right], key=lambda b: -b["bbox"][3])
    remaining = left + right
    ordered = []
    for divider in [*spanning, None]:
        threshold = divider["bbox"][3] if divider else float("-inf")
        band = [b for b in remaining if b["bbox"][3] > threshold]
        ordered.extend(sorted(band, key=lambda b: (b in right, -b["bbox"][3])))
        remaining = [b for b in remaining if b not in band]
        if divider:
            ordered.append(divider)
    return ordered, "two_column_heuristic"


def prepare_document(pages: list[dict]) -> dict:
    """Normalize an extracted layout, retaining raw blocks and exact spans."""
    margins = Counter()
    for page in pages:
        keys = set()
        for block in page["blocks"]:
            x0, y0, x1, y1 = block["bbox"]
            if y0 > page["height"] * .9 or y1 < page["height"] * .1:
                keys.add(normalize_block(block["raw_text"]))
        margins.update(keys)
    output, text_parts, cursor = [], [], 0
    for page in pages:
        blocks, layout = reading_order(page["blocks"], page["width"])
        prepared = []
        for index, block in enumerate(blocks):
            normalized = normalize_block(block["raw_text"])
            bbox = block["bbox"]
            margin = bbox[1] > page["height"] * .9 or bbox[3] < page["height"] * .1
            repeated = len(pages) >= 2 and margins[normalized] >= max(2, len(pages) * .6)
            removed = margin and (repeated or bool(re.fullmatch(r"(?:page\s+)?\d+", normalized, re.I)))
            item = {**block, "block_id": f"p{page['page']}-b{index}", "page": page["page"],
                    "text": normalized, "excluded_margin": removed, "start": None, "end": None}
            if normalized and not removed:
                item.update(start=cursor, end=cursor + len(normalized))
                text_parts.append(normalized)
                cursor += len(normalized) + 2
            prepared.append(item)
        output.append({**page, "blocks": prepared, "layout": layout})
    text = "\n\n".join(text_parts)
    compact = re.sub(r"\s", "", text)
    markers = re.findall(r"\(cid:\d+\)", text)
    marker_chars = sum(map(len, markers))
    readable = re.sub(r"\(cid:\d+\)", "", compact)
    marker_fraction = marker_chars / max(1, len(compact))
    low = (len(readable) < 80 or sum(c.isalpha() for c in readable) / max(1, len(readable)) < .3
           or marker_fraction > .1)
    limitations = ["table_cells_not_reconstructed", "reading_order_is_heuristic"]
    if markers:
        limitations.append("unmapped_font_glyphs")
    if low:
        limitations.append("low_text_quality_or_scanned_pdf")
    return {"backend": "pdfminer", "status": "low_quality" if low else "success",
            "pages": output, "text": text,
            "quality_diagnostics": {"unmapped_glyph_count": len(markers), "unmapped_glyph_fraction": marker_fraction},
            "raw_text": "\f".join("\n".join(b["raw_text"] for b in p["blocks"]) for p in pages),
            "limitations": limitations}


def extract_pdf_document(path) -> dict:
    try:
        pages = []
        for number, layout in enumerate(extract_pages(path, laparams=LAParams(boxes_flow=None)), 1):
            pages.append({"page": number, "width": layout.width, "height": layout.height,
                          "blocks": [{"bbox": list(item.bbox), "raw_text": item.get_text()}
                                     for item in layout if isinstance(item, LTTextContainer)]})
        return prepare_document(pages)
    except Exception as error:
        return {"backend": "pdfminer", "status": "failed", "error_type": type(error).__name__,
                "pages": [], "text": "", "raw_text": "", "limitations": ["extraction_failed"]}
