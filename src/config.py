import os


def _split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def _unique_models(names):
    unique = []
    seen = set()

    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        unique.append(name)

    return unique


DEFAULT_OLLAMA_MODEL_CANDIDATES = ["mistral", "llama3.2:3b", "tinyllama"]
configured_model_candidates = _split_csv(os.getenv("OLLAMA_MODEL_CANDIDATES", ""))

if configured_model_candidates:
    OLLAMA_MODEL_CANDIDATES = _unique_models(configured_model_candidates)
else:
    OLLAMA_MODEL_CANDIDATES = _unique_models(
        [
            os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL_CANDIDATES[0]),
            os.getenv("OLLAMA_FALLBACK_MODEL", DEFAULT_OLLAMA_MODEL_CANDIDATES[1]),
            os.getenv("OLLAMA_SECONDARY_FALLBACK_MODEL", DEFAULT_OLLAMA_MODEL_CANDIDATES[2]),
        ]
    )

MODEL_NAME = OLLAMA_MODEL_CANDIDATES[0]
FALLBACK_MODEL_NAME = OLLAMA_MODEL_CANDIDATES[1] if len(OLLAMA_MODEL_CANDIDATES) > 1 else ""
SECONDARY_FALLBACK_MODEL_NAME = OLLAMA_MODEL_CANDIDATES[2] if len(OLLAMA_MODEL_CANDIDATES) > 2 else ""

# Summary generation is the hot path, so default to a single-pass summary.
ENABLE_SUMMARY_QA = os.getenv("ENABLE_SUMMARY_QA", "false").lower() == "true"

MAX_FEATURED_PAPERS = int(os.getenv("MAX_FEATURED_PAPERS", "12"))
MAX_BRIEF_PAPERS = int(os.getenv("MAX_BRIEF_PAPERS", "13"))
PROCESS_ALL_WHEN_NO_NEW = os.getenv("PROCESS_ALL_WHEN_NO_NEW", "true").lower() == "true"

MAX_SECTION_CHARS = int(os.getenv("MAX_SECTION_CHARS", "5000"))
MAX_SUMMARY_CONTEXT_CHARS = int(os.getenv("MAX_SUMMARY_CONTEXT_CHARS", "6000"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "220"))
OLLAMA_FALLBACK_NUM_PREDICT = int(os.getenv("OLLAMA_FALLBACK_NUM_PREDICT", "140"))
MAX_NARRATIVE_PAPERS = int(os.getenv("MAX_NARRATIVE_PAPERS", "8"))
MAX_NARRATIVE_CONTEXT_CHARS = int(os.getenv("MAX_NARRATIVE_CONTEXT_CHARS", "6000"))
MAX_NARRATIVE_SUMMARY_CHARS = int(os.getenv("MAX_NARRATIVE_SUMMARY_CHARS", "700"))
