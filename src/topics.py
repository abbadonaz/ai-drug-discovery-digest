TOPICS = {
    "Docking & Structure-Based Design": [
        "docking",
        "molecular docking",
        "virtual screening",
        "binding affinity",
        "protein-ligand",
        "ligand binding",
        "scoring function",
        "pose prediction",
        "structure-based drug design",
    ],
    "Computational Chemistry": [
        "computational chemistry",
        "quantum chemistry",
        "density functional theory",
        "dft",
        "molecular dynamics",
        "free energy",
        "fep",
        "force field",
        "ab initio",
        "electronic structure",
    ],
    "QSAR & Property Prediction": [
        "qsar",
        "qspr",
        "property prediction",
        "admet",
        "solubility",
        "toxicity",
        "clearance",
        "permeability",
        "bioactivity prediction",
        "molecular property",
    ],
    "Uncertainty Quantification": [
        "uncertainty quantification",
        "uncertainty estimation",
        "calibration",
        "bayesian neural network",
        "epistemic uncertainty",
        "aleatoric uncertainty",
        "conformal prediction",
        "confidence estimation",
    ],
    "Bayesian Optimization & Active Learning": [
        "bayesian optimization",
        "active learning",
        "closed-loop",
        "adaptive sampling",
        "sequential design",
        "acquisition function",
        "experiment selection",
        "multi-fidelity optimization",
    ],
    "Generative Chemistry": [
        "molecular generation",
        "de novo design",
        "generative model",
        "diffusion model",
        "generative chemistry",
        "molecule design",
        "smiles generation",
        "selfies",
        "reinvent",
        "molecular optimization",
    ],
    "Synthesis-Aware Design": [
        "retrosynthesis",
        "reaction prediction",
        "synthesis planning",
        "synthetic accessibility",
        "synthesizability",
        "synthesis-aware",
        "reaction route",
        "reaction generation",
    ],
}


def score_topics(paper):
    """
    Return a dict of topic -> keyword hit count.
    """
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    scores = {}

    for topic, keywords in TOPICS.items():
        score = 0
        for kw in keywords:
            if kw in text:
                score += 1
        scores[topic] = score

    return scores


def classify_topic(paper):
    """
    Assign the best-matching topic to a paper.
    """
    scores = score_topics(paper)
    best_topic = max(scores, key=scores.get)

    if scores[best_topic] == 0:
        return "Other"

    return best_topic