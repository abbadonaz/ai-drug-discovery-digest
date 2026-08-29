from triage.taxonomy import (
    DOMAIN_SIGNAL_TERMS,
    METHOD_CENTRIC_TOPICS,
    OUT_OF_SCOPE_DOMAIN_TERMS,
    TOPIC_ABSTRACT_WEIGHTS,
    TOPIC_KEYWORDS as TOPICS,
    TOPIC_TITLE_WEIGHTS,
)


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


def has_domain_signal(paper):
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    return any(term in text for term in DOMAIN_SIGNAL_TERMS)


def has_out_of_scope_signal(paper):
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    return any(term in text for term in OUT_OF_SCOPE_DOMAIN_TERMS)


def passes_topic_precision_gate(paper, topic):
    if topic not in METHOD_CENTRIC_TOPICS:
        return not has_out_of_scope_signal(paper)

    return has_domain_signal(paper) and not has_out_of_scope_signal(paper)
