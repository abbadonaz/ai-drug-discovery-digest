from pdf_extract import split_sentences
from clean_sentences import clean_sentences
from embeddings import cosine_similarity, encode_texts
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


def _keyword_bonus(sentence):
    lowered = sentence.lower()
    return sum(weight for keyword, weight in EVIDENCE_KEYWORDS.items() if keyword in lowered)


def _candidate_sentences_from_sections(sections):
    candidates = []

    for section_name, section_text in (sections or {}).items():
        sentences = clean_sentences(split_sentences(section_text))
        for sentence in sentences:
            candidates.append((section_name, sentence))

    return candidates


def select_relevant_evidence(paper, top_k=12):
    candidates = _candidate_sentences_from_sections(paper.get("sections") or {})

    if not candidates:
        fallback = clean_sentences(paper.get("sentences", []))
        candidates = [("ranked_sentences", sentence) for sentence in fallback]

    if not candidates:
        return []

    texts = [sentence for _, sentence in candidates]
    sentence_embeddings = encode_texts(texts)
    interest_embedding = encode_texts([INTEREST_TEXT])[0]

    scored = []
    for (section_name, sentence), embedding in zip(candidates, sentence_embeddings):
        base_score = cosine_similarity(embedding, interest_embedding)
        score = base_score + _keyword_bonus(sentence)
        score *= SECTION_WEIGHTS.get(section_name, 1.0)
        scored.append((score, section_name, sentence))

    scored.sort(key=lambda item: item[0], reverse=True)

    selected = []
    seen = set()
    for _, section_name, sentence in scored:
        normalized = sentence.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        safe_sentence = safe_source_block(sentence, max_chars=500)
        if not safe_sentence:
            continue
        selected.append({"section": section_name, "text": safe_sentence})
        if len(selected) >= top_k:
            break

    return selected


def build_summary_payload(paper, top_k=12):
    evidence = select_relevant_evidence(paper, top_k=top_k)
    lines = []

    for item in evidence:
        section_name = item["section"].replace("_", " ").title()
        lines.append(f"[{section_name}] {item['text']}")

    return {
        "title": paper["title"],
        "url": paper["url"],
        "topic": paper.get("topic", "Other"),
        "evidence": evidence,
        "summary_input": "\n".join(lines),
        "context": safe_source_block(paper.get("context", "")),
    }
