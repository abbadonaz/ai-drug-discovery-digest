from functools import lru_cache

from embeddings import cosine_similarity, encode_texts
from research_taxonomy import (
    AI_CORE_TITLE_TERMS,
    COMPUTATIONAL_CONTEXT_TERMS,
    FIELD_KEYWORDS,
    GENERIC_BIOMEDICAL_TERMS,
    NEGATIVE_KEYWORDS,
    build_interest_text,
)
from topics import classify_topic, score_topics


INTEREST_TEXT = build_interest_text()


@lru_cache(maxsize=1)
def get_interest_embedding():
    return encode_texts([INTEREST_TEXT])[0]


def weighted_keyword_score(text, keywords):
    text = text.lower()
    score = 0

    for keyword, weight in keywords.items():
        if keyword in text:
            score += weight

    return score


def field_signal_score(paper):
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    title_lower = title.lower()

    ai_bonus = sum(1 for term in AI_CORE_TITLE_TERMS if term in title_lower) * 2

    return (
        1.8 * weighted_keyword_score(title, FIELD_KEYWORDS)
        + weighted_keyword_score(abstract, FIELD_KEYWORDS)
        + ai_bonus
    )


def is_weak_docking_match(text):
    lowered = text.lower()
    if "docking" not in lowered:
        return False
    return not any(term in lowered for term in COMPUTATIONAL_CONTEXT_TERMS)


def is_generic_biomedical_match(text):
    lowered = text.lower()
    has_biomedical_pattern = any(term in lowered for term in GENERIC_BIOMEDICAL_TERMS)
    has_computational_context = any(term in lowered for term in COMPUTATIONAL_CONTEXT_TERMS)
    return has_biomedical_pattern and not has_computational_context


def filter_relevant_papers(
    papers,
    threshold=0.23,
    strong_semantic_threshold=0.30,
    fallback_min_results=12,
):
    """
    Filter for field relevance rather than scientific merit.
    The goal is to keep papers that clearly belong to the target domains:
    computational drug discovery, cheminformatics, QSAR/ADMET,
    generative chemistry, uncertainty quantification,
    bayesian optimization, and molecular representation learning.
    """

    interest_embedding = get_interest_embedding()
    texts = [f"{paper['title']} {paper['abstract']}" for paper in papers]
    embeddings = encode_texts(texts)
    filtered = []
    candidates = []

    for paper, text, emb in zip(papers, texts, embeddings):
        semantic_score = float(cosine_similarity(emb, interest_embedding))

        positive_score = field_signal_score(paper)
        negative_score = weighted_keyword_score(text, NEGATIVE_KEYWORDS)

        topic_scores = score_topics(paper)
        max_topic_hits = max(topic_scores.values()) if topic_scores else 0
        topic_total = sum(topic_scores.values()) if topic_scores else 0
        best_topic = classify_topic(paper) if topic_scores else "Other"

        combined_score = (
            0.24 * semantic_score
            + 0.034 * positive_score
            + 0.068 * topic_total
            - 0.020 * negative_score
        )

        has_domain_signal = (
            positive_score >= 4
            or topic_total >= 3
            or (
                semantic_score >= strong_semantic_threshold
                and positive_score >= 2
                and topic_total >= 1
            )
        )

        weak_match = is_weak_docking_match(text)
        generic_biomedical_match = is_generic_biomedical_match(text)
        clearly_irrelevant = negative_score >= 8 and topic_total == 0 and positive_score < 3

        enriched = dict(paper)
        enriched["semantic_score"] = semantic_score
        enriched["positive_score"] = positive_score
        enriched["negative_score"] = negative_score
        enriched["topic_match_score"] = max_topic_hits
        enriched["topic_total_score"] = topic_total
        enriched["topic"] = best_topic if topic_total > 0 else "Other"
        enriched["relevance_score"] = float(combined_score)
        enriched["has_domain_signal"] = has_domain_signal
        enriched["clearly_irrelevant"] = clearly_irrelevant
        enriched["weak_match"] = weak_match
        enriched["generic_biomedical_match"] = generic_biomedical_match
        candidates.append(enriched)

        if (
            has_domain_signal
            and not clearly_irrelevant
            and not weak_match
            and not generic_biomedical_match
            and combined_score >= threshold
        ):
            filtered.append(enriched)

    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)

    if filtered:
        return filtered

    fallback = [
        paper for paper in candidates
        if not paper["clearly_irrelevant"]
        and not paper["weak_match"]
        and not paper["generic_biomedical_match"]
        and (
            paper["has_domain_signal"]
            or paper["positive_score"] >= 2
            or paper["topic_total_score"] > 0
            or paper["semantic_score"] >= 0.18
        )
    ]

    if not fallback:
        fallback = [paper for paper in candidates if not paper["clearly_irrelevant"]]

    fallback.sort(key=lambda x: x["relevance_score"], reverse=True)
    fallback = fallback[:fallback_min_results]

    if fallback:
        print(
            f"Filter fallback activated: no papers met the strict threshold, keeping top {len(fallback)} candidates."
        )

    return fallback
