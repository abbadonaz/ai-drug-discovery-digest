from triage.taxonomy import PAPER_SCORING_KEYWORDS, PAPER_SCORING_NOVELTY


TOPIC_SCORES = {
    "Structure-Based Modeling & Docking": 6,
    "Drug Discovery & Cheminformatics": 5,
    "Generative Chemistry & Molecular Design": 6,
    "QSAR & ADMET": 5,
    "Computational Chemistry": 4,
    "Bayesian Optimization & Active Learning": 6,
    "Uncertainty Quantification": 6,
    "Molecular Representation Learning": 6,
}


def score_paper(paper):
    score = TOPIC_SCORES.get(paper.get("topic", "Other"), 0)
    text = (paper.get("tldr") or "").lower()
    title = (paper.get("title") or "").lower()

    for keyword in PAPER_SCORING_KEYWORDS:
        if keyword in text:
            score += 2
        if keyword in title:
            score += 3

    for keyword in PAPER_SCORING_NOVELTY:
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
