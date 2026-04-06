TOPIC_SCORES = {
    "QSAR & Property Prediction": 3,
    "Docking & Structure-Based Design": 3,
    "Computational Chemistry": 2,
    "Bayesian Optimization & Active Learning": 2,
    "Uncertainty Quantification": 1,
    "Generative Chemistry": 2,
    "Synthesis-Aware Design": 2,
}

KEYWORDS = [
    "drug discovery",
    "docking",
    "binding affinity",
    "protein-ligand",
    "lead optimization",
    "qsar",
    "admet",
    "molecular generation",
    "generative",
    "synthesis",
    "active learning",
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

    for keyword in KEYWORDS:
        if keyword in text:
            score += 2

    for keyword in NOVELTY:
        if keyword in text:
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
