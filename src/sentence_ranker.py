from sentence_transformers import SentenceTransformer
import numpy as np


model = SentenceTransformer("all-MiniLM-L6-v2")


INTEREST_TEXT = """
drug discovery, docking, QSAR, ADMET, molecular design,
generative chemistry, active learning, Bayesian optimization,
computational chemistry
"""


interest_vec = model.encode(INTEREST_TEXT)


def cosine_similarity(a, b):

    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def rank_sentences(sentences, top_k=15):

    ranked = []

    for s in sentences:

        vec = model.encode(s)

        score = cosine_similarity(vec, interest_vec)

        ranked.append((score, s))

    ranked.sort(reverse=True)

    return [s for _, s in ranked[:top_k]]