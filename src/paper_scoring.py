TOPIC_SCORES = {
    "Drug Discovery & Cheminformatics": 5,
    "QSAR & ADMET": 5,
    "Computational Chemistry": 4,
    "Bayesian Optimization & Active Learning": 6,
    "Uncertainty Quantification": 6,
    "Molecular Representation Learning": 6,
}

KEYWORDS = [
    "drug discovery",
    "cheminformatics",
    "binding affinity",
    "protein-ligand",
    "lead optimization",
    "qsar",
    "admet",
    "active learning",
    "bayesian optimization",
    "uncertainty quantification",
    "conformal prediction",
    "calibration",
    "molecular representation",
    "representation learning",
    "molecular machine learning",
    "graph neural network",
    "graph transformer",
    "molecular embedding",
    "molecular language model",
    "fep",
    "fep calculation",
    "free energy perturbation",
]

NOVELTY = [
    "foundation model",
    "diffusion",
    "multimodal",
    "self-supervised",
    "benchmark",
    "state-of-the-art",
]


def score_paper(paper):
    score = TOPIC_SCORES.get(paper.get("topic", "Other"), 0)
    text = (paper.get("tldr") or "").lower()
    title = (paper.get("title") or "").lower()

    for keyword in KEYWORDS:
        if keyword in text:
            score += 2
        if keyword in title:
            score += 3

    for keyword in NOVELTY:
        if keyword in text:
            score += 1
        if keyword in title:
            score += 1

    return score


def rank_papers(summaries):
    scored = []

    for paper in summaries:
        enriched = dict(paper)
        enriched["score"] = score_paper(enriched)
        scored.append(enriched)

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored
