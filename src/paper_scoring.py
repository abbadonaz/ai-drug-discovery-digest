import re

TOPIC_SCORES = {
    "QSAR & Property Prediction": 3,
    "Docking & Structure-Based Design": 3,
    "Computational Chemistry": 2,
    "Bayesian Optimization & Active Learning": 2,
    "Uncertainty Quantification": 1
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

    score = 0

    # topic weight
    score += TOPIC_SCORES.get(paper["topic"], 0)

    text = paper["tldr"].lower()

    # keyword relevance
    for kw in KEYWORDS:
        if kw in text:
            score += 2

    # novelty bonus
    for kw in NOVELTY:
        if kw in text:
            score += 1

    return score


def rank_papers(summaries):

    scored = []

    for paper in summaries:

        s = score_paper(paper)

        paper["score"] = s

        scored.append(paper)

    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored