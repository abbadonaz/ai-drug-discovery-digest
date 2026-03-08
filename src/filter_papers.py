from sentence_transformers import SentenceTransformer
import numpy as np

from topics import score_topics


model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


INTEREST_TEXT = """
machine learning for drug discovery, cheminformatics, molecular docking,
virtual screening, structure-based drug design, protein-ligand modeling,
binding affinity prediction, QSAR, QSPR, ADMET prediction,
computational chemistry for lead optimization, uncertainty quantification,
Bayesian optimization, active learning for molecular design,
generative chemistry, de novo molecular design, synthesis-aware generative models,
REINVENT, molecular representation learning, graph neural networks for molecules
"""


# Positive signals we want to reward
POSITIVE_KEYWORDS = {
    "drug discovery": 3,
    "cheminformatics": 3,
    "docking": 3,
    "molecular docking": 4,
    "virtual screening": 4,
    "protein-ligand": 4,
    "ligand binding": 3,
    "binding affinity": 4,
    "structure-based drug design": 4,
    "qsar": 4,
    "qspr": 4,
    "admet": 4,
    "property prediction": 2,
    "bayesian optimization": 4,
    "active learning": 4,
    "uncertainty quantification": 4,
    "uncertainty estimation": 3,
    "calibration": 2,
    "conformal prediction": 3,
    "generative model": 2,
    "generative chemistry": 4,
    "molecular generation": 4,
    "de novo design": 4,
    "reinvent": 5,
    "retrosynthesis": 4,
    "reaction prediction": 3,
    "synthetic accessibility": 3,
    "synthesis-aware": 4,
    "computational chemistry": 3,
    "quantum chemistry": 2,
    "molecular dynamics": 2,
    "free energy": 3,
    "fep": 3,
    "graph neural network": 2,
    "molecular representation": 3,
}

# Negative signals that often produce irrelevant papers for your use case
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


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def weighted_keyword_score(text, keywords):
    text = text.lower()
    score = 0

    for keyword, weight in keywords.items():
        if keyword in text:
            score += weight

    return score


def filter_relevant_papers(
    papers,
    threshold=0.60,
    strong_semantic_threshold=0.52,
):
    """
    Rank papers by:
    1. semantic similarity
    2. pharma-positive keyword score
    3. topic match strength
    4. negative keyword penalty

    Keeps papers that are both semantically relevant and operationally useful
    for a pharma R&D reader.
    """

    interest_embedding = model.encode(INTEREST_TEXT)
    filtered = []

    for paper in papers:
        text = f"{paper['title']} {paper['abstract']}"

        emb = model.encode(text)
        semantic_score = float(cosine_similarity(emb, interest_embedding))

        positive_score = weighted_keyword_score(text, POSITIVE_KEYWORDS)
        negative_score = weighted_keyword_score(text, NEGATIVE_KEYWORDS)

        topic_scores = score_topics(paper)
        max_topic_hits = max(topic_scores.values()) if topic_scores else 0
        best_topic = max(topic_scores, key=topic_scores.get) if topic_scores else "Other"

        combined_score = (
            semantic_score
            + 0.015 * positive_score
            + 0.040 * max_topic_hits
            - 0.020 * negative_score
        )

        # Gate: require clear domain evidence
        has_domain_signal = (
            positive_score >= 4
            or max_topic_hits >= 2
            or (semantic_score >= strong_semantic_threshold and positive_score >= 2)
        )

        # Hard reject clearly off-domain papers
        clearly_irrelevant = negative_score >= 6 and positive_score <= 2

        if has_domain_signal and not clearly_irrelevant and combined_score >= threshold:
            enriched = dict(paper)
            enriched["semantic_score"] = semantic_score
            enriched["positive_score"] = positive_score
            enriched["negative_score"] = negative_score
            enriched["topic_match_score"] = max_topic_hits
            enriched["topic"] = best_topic if max_topic_hits > 0 else "Other"
            enriched["relevance_score"] = float(combined_score)
            filtered.append(enriched)

    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
    return filtered