from topics import classify_topic, score_topics
from functools import lru_cache
from embeddings import cosine_similarity, encode_texts


INTEREST_TEXT = """
drug discovery, cheminformatics, computer-aided drug design,
computational chemistry, molecular dynamics, quantum chemistry,
uncertainty quantification, uncertainty-aware molecular modeling,
bayesian optimization, active learning, molecular representation learning,
graph neural networks for molecules, molecular embeddings, qsar, admet,
virtual screening, structure-based drug design, binding affinity prediction
"""


FIELD_KEYWORDS = {
    "drug discovery": 4,
    "cheminformatics": 4,
    "computer-aided drug design": 4,
    "cadd": 3,
    "virtual screening": 4,
    "structure-based drug design": 4,
    "binding affinity": 4,
    "protein-ligand": 3,
    "molecular docking": 3,
    "computational chemistry": 4,
    "quantum chemistry": 3,
    "molecular dynamics": 3,
    "free energy": 3,
    "free energy perturbation": 4,
    "fep": 4,
    "qsar": 4,
    "qspr": 4,
    "admet": 4,
    "property prediction": 3,
    "uncertainty quantification": 4,
    "uncertainty estimation": 3,
    "conformal prediction": 3,
    "calibration": 2,
    "bayesian optimization": 4,
    "active learning": 4,
    "molecular representation": 4,
    "representation learning": 3,
    "graph neural network": 3,
    "graph transformer": 3,
    "molecular embedding": 3,
    "molecular fingerprint": 2,
}

NEGATIVE_KEYWORDS = {
    "polymer": 4,
    "polymers": 4,
    "battery": 5,
    "catalyst": 4,
    "catalysis": 4,
    "surface analysis": 4,
    "xps": 6,
    "spectra": 3,
    "spectroscopy": 4,
    "interatomic potential": 4,
    "defect": 4,
    "strong coupling": 4,
    "photonic": 3,
    "reaction kinetics": 3,
    "materials": 4,
    "semiconductor": 5,
    "gas-phase": 3,
    "solvent angular": 5,
    "polymeric": 4,
}

COMPUTATIONAL_CONTEXT_TERMS = [
    "drug discovery",
    "computer-aided drug design",
    "cadd",
    "virtual screening",
    "structure-based drug design",
    "binding affinity",
    "protein-ligand",
    "cheminformatics",
    "computational",
    "in silico",
    "molecular dynamics",
    "free energy",
    "fep",
    "qsar",
    "admet",
    "representation learning",
    "graph neural network",
    "bayesian optimization",
    "active learning",
    "uncertainty",
]

GENERIC_BIOMEDICAL_TERMS = [
    "bioinformatics analysis",
    "network pharmacology",
    "single-cell",
    "transcriptome",
    "transcriptomics",
    "gene expression",
    "immune infiltration",
    "immune microenvironment",
    "mendelian randomization",
    "prognostic",
    "prognosis",
    "biomarker",
    "gut microbiota",
]


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
    return (
        1.8 * weighted_keyword_score(title, FIELD_KEYWORDS)
        + weighted_keyword_score(abstract, FIELD_KEYWORDS)
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
    threshold=0.22,
    strong_semantic_threshold=0.30,
    fallback_min_results=12,
):
    """
    Filter for field relevance rather than scientific merit.
    The goal is to keep papers that clearly belong to the target domains:
    drug discovery, cheminformatics, computational chemistry,
    uncertainty quantification, active learning, bayesian optimization,
    and molecular representation learning.
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
            0.30 * semantic_score
            + 0.030 * positive_score
            + 0.060 * topic_total
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
