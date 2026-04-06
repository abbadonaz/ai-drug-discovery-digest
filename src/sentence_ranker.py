from functools import lru_cache

from embeddings import cosine_similarity, encode_texts


INTEREST_TEXT = """
drug discovery, docking, QSAR, ADMET, molecular design,
generative chemistry, active learning, Bayesian optimization,
computational chemistry
"""


@lru_cache(maxsize=1)
def get_interest_vector():
    return encode_texts([INTEREST_TEXT])[0]


def rank_sentences(sentences, top_k=15):
    if not sentences:
        return []

    sentence_vectors = encode_texts(sentences)
    interest_vec = get_interest_vector()
    ranked = []

    for s, vec in zip(sentences, sentence_vectors):
        score = cosine_similarity(vec, interest_vec)

        ranked.append((score, s))

    ranked.sort(reverse=True)

    return [s for _, s in ranked[:top_k]]
