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
    candidates = _candidate_sentences_from_sections(paper.get("sections") or {})

    if not candidates:
        fallback = clean_sentences(paper.get("sentences", []))
        candidates = [("ranked_sentences", sentence) for sentence in fallback]

    if not candidates:
        return []

    ranked_candidates = _rank_candidates(candidates)
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


def build_summary_payload(paper, top_k=12):
    evidence = select_relevant_evidence(paper, top_k=top_k)
    lines = []

    for item in evidence:
        role_name = item.get("role", "supporting").replace("_", " ").title()
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
