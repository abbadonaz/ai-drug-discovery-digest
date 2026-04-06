TOPICS = {
    "Drug Discovery & Cheminformatics": [
        "drug discovery",
        "cheminformatics",
        "computer-aided drug design",
        "cadd",
        "virtual screening",
        "structure-based drug design",
        "ligand-based drug design",
        "molecular docking",
        "binding affinity",
        "protein-ligand",
        "hit identification",
        "hit-to-lead",
        "lead optimization",
        "pharmacophore",
        "scaffold hopping",
        "molecular design",
        "computational design",
        "dna-encoded library",
    ],
    "Computational Chemistry": [
        "computational chemistry",
        "quantum chemistry",
        "density functional theory",
        "dft",
        "molecular dynamics",
        "free energy",
        "free energy perturbation",
        "fep",
        "force field",
        "ab initio",
        "electronic structure",
        "conformer",
        "reaction mechanism",
        "simulation",
    ],
    "QSAR & ADMET": [
        "qsar",
        "qspr",
        "admet",
        "property prediction",
        "solubility",
        "permeability",
        "clearance",
        "toxicity",
        "bioactivity prediction",
        "molecular property",
    ],
    "Uncertainty Quantification": [
        "uncertainty quantification",
        "uncertainty estimation",
        "calibration",
        "confidence estimation",
        "conformal prediction",
        "epistemic uncertainty",
        "aleatoric uncertainty",
        "uncertainty-aware",
    ],
    "Bayesian Optimization & Active Learning": [
        "bayesian optimization",
        "active learning",
        "closed-loop",
        "adaptive sampling",
        "acquisition function",
        "sequential design",
        "experiment selection",
        "multi-fidelity optimization",
    ],
    "Molecular Representation Learning": [
        "molecular representation",
        "representation learning",
        "molecular embedding",
        "molecular fingerprint",
        "graph neural network",
        "graph transformer",
        "message passing neural network",
        "molecular graph",
        "self-supervised",
        "foundation model for molecules",
    ],
}


def score_topics(paper):
    """
    Return a dict of topic -> weighted keyword hit count.
    Title hits matter more than abstract hits because they are stronger field signals.
    """
    title = paper.get("title", "").lower()
    abstract = paper.get("abstract", "").lower()
    scores = {}

    for topic, keywords in TOPICS.items():
        score = 0
        for keyword in keywords:
            if keyword in title:
                score += 2
            elif keyword in abstract:
                score += 1
        scores[topic] = score

    return scores


def classify_topic(paper):
    scores = score_topics(paper)
    best_topic = max(scores, key=scores.get)

    if scores[best_topic] == 0:
        return "Other"

    return best_topic
