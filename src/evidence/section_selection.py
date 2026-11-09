"""Deterministic section/feature heuristics, not scientific-importance scores."""
from dataclasses import dataclass, field
import re

from digest_core.config import EVIDENCE_CHAR_BUDGET, EVIDENCE_MAX_PASSAGES, MAX_SUMMARY_CONTEXT_CHARS
from evidence.scientific_sections import METHOD_CATEGORIES, abstract_passages
from evidence.security import is_suspicious_text


@dataclass(frozen=True)
class SelectionSettings:
    char_budget: int = EVIDENCE_CHAR_BUDGET
    max_passages: int = EVIDENCE_MAX_PASSAGES
    duplicate_threshold: float = .85
    section_weights: dict[str, float] = field(default_factory=lambda: {
        "results": 3, "methods": 3.5, "limitations": 2.5, "discussion": 1.5,
        "abstract": 1, "conclusion": 1, "introduction": .2, "unknown": 0, "supplementary": .5})
    feature_weights: dict[str, float] = field(default_factory=lambda: {
        "quantitative_metric": 2, "reported_outcome": 3,
        "negative_result": 3, "ablation": -2,
        "validation_protocol": 2, "protocol": 1, "architecture": 2,
        "comparison": 1, "caveat": 1, "domain": .5})
    coverage_order: tuple[str, ...] = ("results", "limitations", "methods")

    def __post_init__(self):
        if not 1 <= self.char_budget <= MAX_SUMMARY_CONTEXT_CHARS or self.max_passages < 1:
            raise ValueError("Evidence budget must fit MAX_SUMMARY_CONTEXT_CHARS and passage count must be positive")
        if not 0 <= self.duplicate_threshold <= 1:
            raise ValueError("Duplicate threshold must be within [0,1]")


def family(section):
    if section in METHOD_CATEGORIES:
        return "methods"
    return "results" if section == "results_discussion" else section


def features(text: str) -> dict[str, bool]:
    return {
        "quantitative_metric": bool(re.search(r"\d", text) and re.search(r"\b(AUROC|AUC|AULC|RMSE|MAE|accuracy|coverage|sharpness|enrichment|scores?|success rate|win rates?|queries|validity|novelty|diversity|uniqueness|p\s*[<=>])\b", text, re.I)),
        "reported_outcome": bool(re.search(r"\d", text) and not re.search(r"\bdefined as\b", text, re.I)
                                 and re.search(r"\b(achieves?|reaches?|yield(?:s|ing)?|sav(?:es?|ing)|gains?|speedups?|outperforms?|wins?\s+\d+|increases?|rising from)\b", text, re.I)),
        "negative_result": bool(re.search(
            r"\b(?:not statistically significant|"
            r"no significant (?:difference|improvement))\b",
            text, re.I)),
        "ablation": bool(re.search(
            r"\b(?:ablation|acquisition variants|disagreement-only)\b", text, re.I)),
        "architecture": bool(re.search(
            r"\barchi-?tecture\b[^.!?]{0,60}"
            r"\b(?:composed of|consists of|comprises)\b", text, re.I)),
        "protocol": bool(re.search(r"\b(scaffold|temporal|random split|external validation|cross.validation|prospective|retrospective|dataset|acquisition|calibrat|training|test set)", text, re.I)),
        "validation_protocol": bool(re.search(
            r"\b(scaffold|train.test|locked set|held.out|five folds|"
            r"cross.validation|random seeds|validation split|evaluation metrics)\b",
            text, re.I)),
        "comparison": bool(re.search(r"\b(versus|compared|baseline|relative to|ablation|outperform)", text, re.I)),
        "caveat": bool(re.search(r"\b(limit|bias|shift|not synthes|no experimental|not measured|applicability|uncertain|no external)", text, re.I)),
        "domain": bool(re.search(r"\b(molecul|compound|QSAR|ADMET|graph neural|descriptor|docking|binding|molecular dynamics|synthetic accessibility|multi.parameter)", text, re.I)),
    }


def format_passage(item):
    page = item.get("page_start")
    return f"[{item['passage_id']} | {item['section']} | page {page if page is not None else 'unknown'}] {item['text']}"


def near_duplicate(left, right, threshold):
    # Numerically different comparisons must not be erased as near duplicates.
    if re.findall(r"[-+]?\d+(?:\.\d+)?", left) != re.findall(r"[-+]?\d+(?:\.\d+)?", right):
        return False
    normalized_left, normalized_right = left.casefold().strip(), right.casefold().strip()
    # A source abstract sentence and a PDF abstract paragraph can carry the same
    # sentence at different granularity. Don't spend budget on both versions.
    if normalized_left in normalized_right or normalized_right in normalized_left:
        return True
    a, b = set(re.findall(r"\w+", left.lower())), set(re.findall(r"\w+", right.lower()))
    return len(a & b) / max(1, len(a | b)) >= threshold


def select_passages(paper: dict, settings: SelectionSettings | None = None) -> tuple[list[dict], dict]:
    settings = settings or SelectionSettings(char_budget=paper.get("evidence_char_budget", EVIDENCE_CHAR_BUDGET))
    candidates = paper.get("passages") or abstract_passages(paper)
    ranked, excluded = [], {
        "references": 0, "unsafe": 0, "numeric_block": 0, "font_glyphs": 0,
        "caption_only": 0, "budget": 0, "duplicate": 0,
    }
    signals_by_id = {}
    for passage in candidates:
        item = dict(passage)
        if item["section"] == "references":
            excluded["references"] += 1
            continue
        if is_suspicious_text(item["text"]):
            excluded["unsafe"] += 1
            continue
        if "ambiguous_numeric_block" in item.get("limitations", []):
            excluded["numeric_block"] += 1
            continue
        if "(cid:" in item["text"]:
            excluded["font_glyphs"] += 1
            continue
        if len(item["text"]) < 35:
            continue
        signals = features(item["text"])
        if (re.match(r"^(?:Fig(?:ure)?\.?|Table)\s+\d", item["text"], re.I)
                and not any(signals[name] for name in (
                    "protocol", "validation_protocol", "quantitative_metric",
                    "reported_outcome", "architecture"))):
            excluded["caption_only"] += 1
            continue
        section = family(item["section"])
        # "To achieve this" in an architecture is not a reported result.
        for name in ("reported_outcome", "quantitative_metric"):
            signals[name] = signals[name] and section == "results"
        signals["architecture"] = signals["architecture"] and section == "methods"
        signals_by_id[item["passage_id"]] = signals
        score = settings.section_weights.get(section, 0)
        score += sum(settings.feature_weights.get(name, 0) for name, active in signals.items() if active)
        item.update(score=score, selection_reasons=["section_prior:" + family(item["section"]),
                                                  *[name for name, active in signals.items() if active]],
                    evidence_id=item["passage_id"], support_status="unverified")
        item["role"] = "method" if section == "methods" else "findings" if section == "results" else "problem"
        item["summary_role"] = "approach" if section == "methods" else "result" if section == "results" else "context" if section == "limitations" else "overview"
        ranked.append(item)
    ranked.sort(key=lambda item: (-item["score"], item["passage_id"]))
    selected, used, rejected = [], 0, set()

    def pick(item, coverage=False):
        nonlocal used
        if item in selected or item["passage_id"] in rejected or len(selected) >= settings.max_passages:
            return False
        if any(near_duplicate(item["text"], other["text"], settings.duplicate_threshold) for other in selected):
            excluded["duplicate"] += 1
            rejected.add(item["passage_id"])
            return False
        cost = len(format_passage(item)) + bool(selected)
        if used + cost > settings.char_budget:
            excluded["budget"] += 1
            rejected.add(item["passage_id"])
            return False
        if coverage:
            item["selection_reasons"].append("category_coverage")
        selected.append(item)
        used += cost
        return True

    for category in settings.coverage_order:
        if category == "limitations":
            category_ranked = sorted(ranked, key=lambda p: (
                not signals_by_id[p["passage_id"]]["caveat"],
                -p["score"], p["passage_id"]))
        elif category == "results":
            category_ranked = sorted(ranked, key=lambda p: (
                not signals_by_id[p["passage_id"]]["negative_result"],
                not (signals_by_id[p["passage_id"]]["quantitative_metric"]
                     and signals_by_id[p["passage_id"]]["reported_outcome"]),
                -p["score"], p["passage_id"]))
        elif category == "methods":
            category_ranked = sorted(ranked, key=lambda p: (
                not signals_by_id[p["passage_id"]]["validation_protocol"],
                -p["score"], p["passage_id"]))
        else:
            category_ranked = ranked
        for item in category_ranked:
            if family(item["section"]) == category and pick(item, True):
                break
    for item in ranked:
        # A favorable result inherited under a limitations heading must not
        # displace protocol evidence once an actual author caveat is selected.
        if (family(item["section"]) == "limitations"
                and not signals_by_id[item["passage_id"]]["caveat"]
                and any(family(p["section"]) == "limitations" for p in selected)):
            continue
        pick(item)
    return selected, {"strategy": "section_aware", "candidate_count": len(candidates),
                      "eligible_count": len(ranked), "selected_count": len(selected), "input_chars": used,
                      "char_budget": settings.char_budget, "excluded": excluded,
                      "available_abstract_chars": len(paper.get("abstract", "")),
                      "selected_abstract_chars": sum(len(p["text"]) for p in selected if p["section"] == "abstract"),
                      "missing_coverage": [category for category in settings.coverage_order
                                           if category not in {family(item['section']) for item in selected}],
                      "status": "selected" if selected else "no_eligible_evidence"}


def build_section_payload(paper: dict, settings: SelectionSettings | None = None) -> dict:
    evidence, diagnostics = select_passages(paper, settings)
    text = "\n".join(format_passage(item) for item in evidence)
    return {"title": paper["title"], "url": paper["url"], "topic": paper.get("topic", "Other"),
            "evidence": evidence, "summary_input": text, "context": text,
            "evidence_strategy": "section_aware", "char_budget": diagnostics["char_budget"],
            "selection_diagnostics": diagnostics}
