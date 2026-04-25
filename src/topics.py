from research_taxonomy import (
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
