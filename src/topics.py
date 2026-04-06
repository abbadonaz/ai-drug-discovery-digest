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
        "ligand generation",
        "hit expansion",
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
        "coarse-grained",
        "qm/mm",
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
        "predictive uncertainty",
        "out-of-distribution",
        "distribution shift",
        "confidence calibration",
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
        "pool-based active learning",
        "uncertainty sampling",
        "expected improvement",
        "thompson sampling",
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
        "pretrained molecular model",
        "graph pretraining",
        "contrastive learning",
        "equivariant graph neural network",
        "smiles encoder",
        "molecular language model",
    ],
}


TOPIC_TITLE_WEIGHTS = {
    "Drug Discovery & Cheminformatics": 2,
    "Computational Chemistry": 2,
    "QSAR & ADMET": 2,
    "Uncertainty Quantification": 3,
    "Bayesian Optimization & Active Learning": 3,
    "Molecular Representation Learning": 3,
}

TOPIC_ABSTRACT_WEIGHTS = {
    "Drug Discovery & Cheminformatics": 1,
    "Computational Chemistry": 1,
    "QSAR & ADMET": 1,
    "Uncertainty Quantification": 2,
    "Bayesian Optimization & Active Learning": 2,
    "Molecular Representation Learning": 2,
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
        title_weight = TOPIC_TITLE_WEIGHTS.get(topic, 2)
        abstract_weight = TOPIC_ABSTRACT_WEIGHTS.get(topic, 1)
        for keyword in keywords:
            if keyword in title:
                score += title_weight
            elif keyword in abstract:
                score += abstract_weight
        scores[topic] = score

    return scores


def classify_topic(paper):
    scores = score_topics(paper)
    best_topic = max(scores, key=scores.get)

    if scores[best_topic] == 0:
        return "Other"

    return best_topic
