from collections import Counter, defaultdict
import math

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from digest_core.models import PipelineSettings
from triage.embeddings import cosine_similarity, encode_texts


def cluster_and_select_papers(papers, settings: PipelineSettings):
    if not papers:
        return [], []

    clustered = cluster_papers(papers, settings=settings)
    representatives = select_cluster_representatives(clustered, settings=settings)
    representative_urls = {paper["url"] for paper in representatives}
    remaining = [paper for paper in clustered if paper["url"] not in representative_urls]
    remaining.sort(key=lambda paper: paper.get("selection_score", paper.get("relevance_score", 0)), reverse=True)
    return clustered, representatives + remaining


def cluster_papers(papers, settings: PipelineSettings | None = None):
    if len(papers) == 1:
        enriched = dict(papers[0])
        enriched.update({
            "cluster_id": 0,
            "cluster_label": enriched.get("topic", "Other"),
            "cluster_size": 1,
            "representativeness_score": 1.0,
            "selection_score": float(enriched.get("relevance_score", 0)),
        })
        return [enriched]

    settings = settings or PipelineSettings()
    texts = [f"{paper.get('title', '')} {paper.get('abstract', '')}" for paper in papers]
    embeddings = np.array(encode_texts(texts), dtype=float)
    labels = _cluster_labels(embeddings)

    grouped = defaultdict(list)
    for index, label in enumerate(labels):
        grouped[int(label)].append(index)

    enriched = [dict(paper) for paper in papers]
    relevance_values = [float(paper.get("relevance_score", 0)) for paper in papers]
    normalized_relevance = _normalize(relevance_values)
    representative_scores = [0.0 for _ in papers]

    for cluster_id, indices in grouped.items():
        centroid = np.mean(embeddings[indices], axis=0)
        label = _cluster_label([papers[index] for index in indices])

        for index in indices:
            score = float(cosine_similarity(embeddings[index], centroid))
            representative_scores[index] = score
            enriched[index]["cluster_id"] = cluster_id
            enriched[index]["cluster_label"] = label
            enriched[index]["cluster_size"] = len(indices)

    normalized_representativeness = _normalize(representative_scores)

    for index, paper in enumerate(enriched):
        relevance = normalized_relevance[index]
        representativeness = normalized_representativeness[index]
        paper["representativeness_score"] = representative_scores[index]
        paper["selection_score"] = (
            settings.cluster_relevance_weight * relevance
            + settings.cluster_representativeness_weight * representativeness
        )

    return enriched


def select_cluster_representatives(clustered_papers, settings: PipelineSettings | None = None):
    if not clustered_papers:
        return []

    settings = settings or PipelineSettings()
    grouped = defaultdict(list)
    for paper in clustered_papers:
        grouped[paper.get("cluster_id", -1)].append(paper)

    selected = []
    for _, papers in sorted(grouped.items(), key=lambda item: _cluster_priority(item[1]), reverse=True):
        papers = sorted(papers, key=lambda paper: paper.get("selection_score", 0), reverse=True)
        selected.extend(papers[:_representative_count(len(papers))])
        if len(selected) >= settings.max_featured_papers:
            break

    selected.sort(key=lambda paper: paper.get("selection_score", 0), reverse=True)
    return selected[:settings.max_featured_papers]


def build_cluster_overviews(clustered_papers):
    grouped = defaultdict(list)
    for paper in clustered_papers:
        grouped[paper.get("cluster_id", -1)].append(paper)

    overviews = {}
    for cluster_id, papers in grouped.items():
        label = papers[0].get("cluster_label", "Other")
        top_titles = [paper.get("title", "") for paper in sorted(papers, key=lambda item: item.get("selection_score", 0), reverse=True)[:3]]
        overviews[cluster_id] = (
            f"{label} is represented by {len(papers)} paper(s) in this batch. "
            f"Representative work includes: {'; '.join(title for title in top_titles if title)}."
        )

    return overviews


def _cluster_labels(embeddings):
    n_papers = len(embeddings)
    n_clusters = max(1, min(6, round(math.sqrt(n_papers))))
    if n_clusters <= 1:
        return [0 for _ in range(n_papers)]

    try:
        model = AgglomerativeClustering(n_clusters=n_clusters, metric="cosine", linkage="average")
    except TypeError:
        model = AgglomerativeClustering(n_clusters=n_clusters, affinity="cosine", linkage="average")

    return model.fit_predict(embeddings)


def _cluster_label(papers):
    topics = [paper.get("topic") or "Other" for paper in papers]
    return Counter(topics).most_common(1)[0][0]


def _cluster_priority(papers):
    return max(paper.get("selection_score", 0) for paper in papers)


def _representative_count(cluster_size):
    if cluster_size >= 8:
        return 3
    if cluster_size >= 4:
        return 2
    return 1


def _normalize(values):
    if not values:
        return []

    minimum = min(values)
    maximum = max(values)
    if maximum == minimum:
        return [1.0 for _ in values]

    return [(value - minimum) / (maximum - minimum) for value in values]
