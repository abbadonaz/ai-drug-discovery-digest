from functools import lru_cache
import re

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - dependency availability depends on local setup
    SentenceTransformer = None


HASH_DIM = 256
TOKEN_PATTERN = re.compile(r"[a-z0-9\-\+]+")


@lru_cache(maxsize=1)
def get_embedding_model():
    if SentenceTransformer is None:
        return None

    try:
        return SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            local_files_only=True,
        )
    except Exception:
        return None


def _hashed_text_vector(text):
    vector = np.zeros(HASH_DIM, dtype=float)
    tokens = TOKEN_PATTERN.findall((text or "").lower())

    if not tokens:
        return vector

    for token in tokens:
        bucket = hash(token) % HASH_DIM
        vector[bucket] += 1.0

    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def encode_texts(texts):
    if not texts:
        return np.array([])

    model = get_embedding_model()
    if model is not None:
        return model.encode(texts)

    return np.array([_hashed_text_vector(text) for text in texts])


def cosine_similarity(a, b):
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)
