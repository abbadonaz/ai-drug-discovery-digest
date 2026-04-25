import re

from clean_sentences import clean_sentences
from embeddings import cosine_similarity, encode_texts
from pdf_extract import split_sentences
from security import safe_source_block


INTEREST_TEXT = """
scientific contributions in drug discovery, cheminformatics, computational chemistry,
molecular machine learning, docking, virtual screening, ADMET, QSAR,
binding affinity prediction, molecular generation, active learning
"""

SECTION_WEIGHTS = {
    "abstract": 1.35,
    "results": 1.25,
    "conclusion": 1.2,
    "discussion": 1.1,
    "methods": 0.95,
    "introduction": 0.9,
}

EVIDENCE_KEYWORDS = {
    "outperform": 0.2,
    "benchmark": 0.2,
    "state-of-the-art": 0.2,
    "binding affinity": 0.25,
    "virtual screening": 0.25,
    "admet": 0.25,
    "docking": 0.25,
    "qsar": 0.2,
    "auc": 0.15,
    "rmse": 0.15,
    "mae": 0.15,
    "improv": 0.15,
}

ROLE_KEYWORDS = {
    "problem": {
        "bottleneck": 0.35,
        "challenge": 0.35,
        "goal": 0.15,
        "investigate": 0.2,
        "limitation": 0.35,
        "problem": 0.35,
        "poorly understood": 0.45,
        "remains unclear": 0.45,
        "we study": 0.2,
        "we investigate": 0.25,
    },
    "method": {
        "algorithm": 0.2,
        "approach": 0.25,
        "diagnostic": 0.15,
        "framework": 0.25,
        "method": 0.2,
        "model": 0.15,
        "pipeline": 0.15,
        "protocol": 0.1,
        "propose": 0.4,
        "presented": 0.35,
        "trained": 0.15,
        "we develop": 0.4,
        "we introduce": 0.4,
        "we present": 0.4,
        "we propose": 0.45,
        "we presented": 0.45,
    },
    "dataset": {
        "benchmark": 0.45,
        "cohort": 0.25,
        "dataset": 0.45,
        "evaluated on": 0.35,
        "evaluation": 0.2,
        "experiments on": 0.3,
        "screening": 0.15,
        "tested on": 0.3,
        "validation": 0.2,
    },
    "findings": {
        "achiev": 0.35,
        "decrease": 0.2,
        "demonstrat": 0.2,
        "identified": 0.25,
        "improv": 0.45,
        "increase": 0.2,
        "outperform": 0.5,
        "reduced": 0.2,
        "show": 0.2,
        "significant": 0.2,
        "suppressed": 0.2,
    },
}

ROLE_MIN_BONUS = {
    "problem": 0.2,
    "method": 0.2,
    "dataset": 0.15,
    "findings": 0.15,
}

ROLE_SECTION_WEIGHTS = {
    "problem": {
        "abstract": 1.2,
        "introduction": 1.2,
        "discussion": 1.05,
        "conclusion": 0.95,
        "methods": 0.8,
        "results": 0.9,
    },
    "method": {
        "abstract": 1.15,
        "methods": 1.25,
        "introduction": 0.95,
        "results": 0.9,
        "discussion": 0.85,
        "conclusion": 0.85,
    },
    "dataset": {
        "abstract": 1.05,
        "methods": 1.1,
        "results": 1.15,
        "discussion": 0.85,
        "conclusion": 0.85,
        "introduction": 0.85,
    },
    "findings": {
        "abstract": 1.1,
        "results": 1.3,
        "discussion": 1.05,
        "conclusion": 1.0,
        "methods": 0.8,
        "introduction": 0.85,
    },
}

ROLE_TARGETS = {
    "problem": 2,
    "method": 2,
    "dataset": 1,
    "findings": 3,
}

LOW_INFORMATION_ROLES = {"problem", "method", "findings"}
ROLE_SELECTION_ORDER = ["problem", "method", "findings", "dataset"]
SUMMARY_SLOT_PREFERENCES = [
    {
        "summary_role": "overview",
        "roles": ("problem", "method", "supporting"),
        "sections": ("abstract", "introduction", "conclusion", "discussion", "results", "ranked_sentences"),
    },
    {
        "summary_role": "approach",
        "roles": ("method", "supporting", "problem"),
        "sections": ("abstract", "methods", "introduction", "results", "ranked_sentences"),
    },
    {
        "summary_role": "result",
        "roles": ("findings", "supporting", "dataset"),
        "sections": ("results", "conclusion", "discussion", "abstract", "ranked_sentences"),
    },
]
SUMMARY_SLOT_KEYWORDS = {
    "overview": {
        "this paper": 0.55,
        "this study": 0.8,
        "this work": 0.8,
        "in this work": 0.85,
        "we develop": 0.8,
        "we evaluate": 0.6,
        "we introduce": 0.8,
        "we investigate": 0.65,
        "we present": 0.8,
        "we propose": 0.8,
        "we study": 0.8,
        "review": 0.45,
        "survey": 0.45,
    },
    "approach": {
        "approach": 0.35,
        "combining": 0.25,
        "contrastive": 0.2,
        "framework": 0.4,
        "integrat": 0.2,
        "machine learning": 0.2,
        "method": 0.35,
        "model": 0.35,
        "pipeline": 0.3,
        "qsar": 0.2,
        "random forest": 0.2,
        "using": 0.15,
        "virtual screening": 0.15,
        "workflow": 0.25,
    },
    "result": {
        "achiev": 0.3,
        "assay": 0.3,
        "auc": 0.25,
        "benchmark": 0.35,
        "demonstrat": 0.25,
        "findings": 0.2,
        "identif": 0.35,
        "indicat": 0.25,
        "improv": 0.35,
        "mic": 0.35,
        "outperform": 0.35,
        "performance": 0.2,
        "precision": 0.2,
        "recall": 0.2,
        "results": 0.2,
        "show": 0.2,
        "yielding": 0.2,
        "yielded": 0.25,
        "zero-shot": 0.2,
    },
}
TITLE_OVERLAP_STOPWORDS = {
    "about",
    "across",
    "against",
    "approach",
    "based",
    "disease",
    "drug",
    "from",
    "highly",
    "identification",
    "identifies",
    "integrating",
    "learning",
    "models",
    "molecular",
    "novel",
    "paper",
    "predictive",
    "study",
    "using",
    "with",
}
BACKGROUND_PENALTIES = (
    "continues to restrict",
    "faces the dual challenge",
    "is a progressive",
    "is often described as",
    "is overexpressed",
    "plays a central role",
    "remains a major therapeutic challenge",
    "remains unclear",
)
PROMOTIONAL_PENALTIES = (
    "in summary",
    "our study confirms",
    "our work provides",
    "promising",
    "provides a robust paradigm",
    "valuable contribution",
)


def _keyword_bonus(sentence):
    lowered = sentence.lower()
    return sum(weight for keyword, weight in EVIDENCE_KEYWORDS.items() if keyword in lowered)


def _role_bonus(sentence, role):
    lowered = sentence.lower()
    return sum(weight for keyword, weight in ROLE_KEYWORDS[role].items() if keyword in lowered)


def _candidate_sentences_from_sections(sections):
    candidates = []

    for section_name, section_text in (sections or {}).items():
        sentences = clean_sentences(split_sentences(section_text))
        for sentence in sentences:
            candidates.append((section_name, sentence))

    return candidates


def _ranked_candidates_for_paper(paper):
    candidates = _candidate_sentences_from_sections(paper.get("sections") or {})

    if not candidates:
        fallback = clean_sentences(paper.get("sentences", []))
        candidates = [("ranked_sentences", sentence) for sentence in fallback]

    if not candidates:
        return []

    return _rank_candidates(candidates)


def _rank_candidates(candidates):
    texts = [sentence for _, sentence in candidates]
    sentence_embeddings = encode_texts(texts)
    interest_embedding = encode_texts([INTEREST_TEXT])[0]
    ranked = []

    for (section_name, sentence), embedding in zip(candidates, sentence_embeddings):
        base_score = cosine_similarity(embedding, interest_embedding)
        score = (base_score + _keyword_bonus(sentence)) * SECTION_WEIGHTS.get(section_name, 1.0)
        ranked.append({
            "base_score": base_score,
            "score": score,
            "section": section_name,
            "text": sentence,
        })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def _infer_candidate_role(candidate):
    best_role = "supporting"
    best_score = 0.0

    for role in ROLE_SELECTION_ORDER:
        role_score = _role_bonus(candidate["text"], role)
        if role_score < ROLE_MIN_BONUS[role]:
            continue

        role_score *= ROLE_SECTION_WEIGHTS[role].get(candidate["section"], 1.0)
        if role_score > best_score:
            best_score = role_score
            best_role = role

    return best_role


def _select_role_evidence(ranked_candidates, role, selected, seen):
    picked = []

    role_ranked = []
    for candidate in ranked_candidates:
        role_bonus = _role_bonus(candidate["text"], role)
        if role_bonus < ROLE_MIN_BONUS[role]:
            continue

        role_score = candidate["score"] + role_bonus
        role_score *= ROLE_SECTION_WEIGHTS[role].get(candidate["section"], 1.0)
        role_ranked.append((role_score, candidate))

    role_ranked.sort(key=lambda item: item[0], reverse=True)

    for role_score, candidate in role_ranked:
        if role_score <= 0:
            continue

        normalized = candidate["text"].lower()
        if normalized in seen:
            continue

        safe_sentence = safe_source_block(candidate["text"], max_chars=500)
        if not safe_sentence:
            continue

        selected_item = {
            "role": role,
            "section": candidate["section"],
            "text": safe_sentence,
            "score": role_score,
        }
        selected.append(selected_item)
        picked.append(selected_item)
        seen.add(normalized)

        if len(picked) >= ROLE_TARGETS[role]:
            break

    return picked


def select_relevant_evidence(paper, top_k=12):
    ranked_candidates = _ranked_candidates_for_paper(paper)
    if not ranked_candidates:
        return []

    selected = []
    seen = set()

    for role in ROLE_SELECTION_ORDER:
        _select_role_evidence(ranked_candidates, role, selected, seen)

    for candidate in ranked_candidates:
        normalized = candidate["text"].lower()
        if normalized in seen:
            continue

        safe_sentence = safe_source_block(candidate["text"], max_chars=500)
        if not safe_sentence:
            continue

        selected.append({
            "role": "supporting",
            "section": candidate["section"],
            "text": safe_sentence,
            "score": candidate["score"],
        })
        seen.add(normalized)

        if len(selected) >= top_k:
            break

    return selected[:top_k]


def has_sufficient_summary_evidence(paper, min_sentences=3):
    evidence = select_relevant_evidence(paper, top_k=6)
    informative = [item for item in evidence if item.get("role") in LOW_INFORMATION_ROLES]

    if len(evidence) < min_sentences:
        return False

    if len(informative) < 2:
        return False

    unique_roles = {item.get("role") for item in informative}
    if len(unique_roles) < 2:
        return False

    combined_length = sum(len(item.get("text", "")) for item in evidence)
    return combined_length >= 320


def _summary_title_tokens(title):
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (title or "").lower())
        if len(token) >= 4 and token not in TITLE_OVERLAP_STOPWORDS
    }


def _title_overlap_bonus(text, title):
    title_tokens = _summary_title_tokens(title)
    if not title_tokens:
        return 0.0

    sentence_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(token) >= 4
    }
    overlap = sentence_tokens & title_tokens
    if not overlap:
        return 0.0

    bonus = 0.18 * len(overlap)
    if len(overlap) >= 3:
        bonus += 0.15

    return min(bonus, 0.9)


def _has_study_cue(text):
    lowered = (text or "").lower()
    return any(
        cue in lowered
        for cue in (
            "in this work",
            "this paper",
            "this study",
            "this work",
            "we develop",
            "we evaluate",
            "we introduce",
            "we investigate",
            "we present",
            "we propose",
            "we study",
        )
    )


def _has_method_cue(text):
    lowered = (text or "").lower()
    return any(
        cue in lowered
        for cue in (
            "approach",
            "combining",
            "contrastive",
            "docking",
            "framework",
            "machine learning",
            "method",
            "model",
            "molecular dynamics",
            "pipeline",
            "qsar",
            "random forest",
            "using",
            "virtual screening",
            "workflow",
        )
    )


def _has_result_cue(text):
    lowered = (text or "").lower()
    return any(
        cue in lowered
        for cue in (
            "achiev",
            "assay",
            "auc",
            "benchmark",
            "demonstrat",
            "findings",
            "identified",
            "indicat",
            "improv",
            "mic",
            "outperform",
            "performance",
            "precision",
            "recall",
            "results",
            "show",
            "yielding",
            "yielded",
            "zero-shot",
        )
    )


def _summary_slot_penalty(text, summary_role):
    lowered = (text or "").lower()
    penalty = 0.0

    if any(fragment in lowered for fragment in BACKGROUND_PENALTIES):
        if summary_role == "overview" and not _has_study_cue(lowered):
            penalty += 0.7
        if summary_role == "result":
            penalty += 0.45

    if any(fragment in lowered for fragment in PROMOTIONAL_PENALTIES):
        if summary_role == "overview":
            penalty += 0.65
        elif summary_role in {"approach", "result"}:
            penalty += 0.55

    if summary_role == "approach" and not _has_method_cue(lowered):
        penalty += 0.2

    if summary_role == "result" and not _has_result_cue(lowered):
        penalty += 0.35

    return penalty


def _summary_slot_score(item, summary_role, preferred_roles, preferred_sections, title):
    text = item.get("text", "")
    role = item.get("role", "supporting")
    section = item.get("section", "ranked_sentences")
    lowered = text.lower()

    score = item.get("score", 0.0)
    score += _title_overlap_bonus(text, title)
    score += sum(
        weight
        for keyword, weight in SUMMARY_SLOT_KEYWORDS[summary_role].items()
        if keyword in lowered
    )

    if role in preferred_roles:
        score += 0.18 * (len(preferred_roles) - preferred_roles.index(role))

    if section in preferred_sections:
        score += 0.12 * (len(preferred_sections) - preferred_sections.index(section))

    if summary_role == "overview" and _has_study_cue(lowered):
        score += 0.35
    if summary_role == "approach" and _has_method_cue(lowered):
        score += 0.2
    if summary_role == "result" and _has_result_cue(lowered):
        score += 0.2
        score += 0.08 * item.get("position", 0)

    score -= _summary_slot_penalty(text, summary_role)
    return score


def _pick_summary_item(candidates, summary_role, preferred_roles, preferred_sections, title, seen):
    best_item = None
    best_key = None

    for item in candidates:
        text = (item.get("text") or "").strip()
        if not text:
            continue

        normalized = text.lower()
        if normalized in seen:
            continue

        candidate_key = (
            -_summary_slot_score(item, summary_role, preferred_roles, preferred_sections, title),
            -_title_overlap_bonus(text, title),
            -len(text),
        )

        if best_key is None or candidate_key < best_key:
            best_key = candidate_key
            best_item = item

    return best_item


def select_summary_evidence(paper, max_items=3):
    title = paper.get("title", "")
    abstract_text = ((paper.get("sections") or {}).get("abstract") or "").strip()
    abstract_candidates = []

    for index, sentence in enumerate(clean_sentences(split_sentences(abstract_text, min_chars=0, max_chars=1000))):
        safe_sentence = safe_source_block(sentence, max_chars=500)
        if not safe_sentence:
            continue

        candidate = {
            "position": index,
            "role": _infer_candidate_role({"section": "abstract", "text": safe_sentence}),
            "section": "abstract",
            "text": safe_sentence,
            "score": _keyword_bonus(safe_sentence),
        }
        abstract_candidates.append(candidate)

    selected = []
    seen = set()

    for slot in SUMMARY_SLOT_PREFERENCES:
        item = _pick_summary_item(
            abstract_candidates,
            slot["summary_role"],
            slot["roles"],
            slot["sections"],
            title,
            seen,
        )
        if not item:
            continue

        copied = dict(item)
        copied["summary_role"] = slot["summary_role"]
        selected.append(copied)
        seen.add(copied["text"].lower())

    evidence = select_relevant_evidence(paper, top_k=10)

    if len(selected) < len(SUMMARY_SLOT_PREFERENCES):
        for slot in SUMMARY_SLOT_PREFERENCES:
            if any(item.get("summary_role") == slot["summary_role"] for item in selected):
                continue

            item = _pick_summary_item(
                evidence,
                slot["summary_role"],
                slot["roles"],
                slot["sections"],
                title,
                seen,
            )
            if not item:
                continue

            copied = dict(item)
            copied["summary_role"] = slot["summary_role"]
            selected.append(copied)
            seen.add(copied["text"].lower())

    if len(selected) < 2:
        fallback_sections = ("abstract", "results", "conclusion", "introduction", "discussion", "ranked_sentences")
        while len(selected) < max_items:
            item = _pick_summary_item(
                evidence,
                "overview",
                ("supporting", "method", "findings", "problem", "dataset"),
                fallback_sections,
                title,
                seen,
            )
            if not item:
                break
            copied = dict(item)
            copied["summary_role"] = copied.get("summary_role", "context")
            selected.append(copied)
            seen.add(copied["text"].lower())

    return selected[:max_items]


def build_summary_payload(paper, top_k=12):
    evidence = select_summary_evidence(paper, max_items=min(top_k, 4))
    lines = []

    for item in evidence:
        role_name = item.get("summary_role") or item.get("role", "supporting")
        role_name = role_name.replace("_", " ").title()
        section_name = item["section"].replace("_", " ").title()
        lines.append(f"[{role_name} | {section_name}] {item['text']}")

    return {
        "title": paper["title"],
        "url": paper["url"],
        "topic": paper.get("topic", "Other"),
        "evidence": evidence,
        "summary_input": "\n".join(lines),
        "context": safe_source_block(paper.get("context", "")),
    }
