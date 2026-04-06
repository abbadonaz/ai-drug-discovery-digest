import os


MODEL_NAME = os.getenv("OLLAMA_MODEL", "mistral")
FALLBACK_MODEL_NAME = os.getenv("OLLAMA_FALLBACK_MODEL", "tinyllama")

# Summary generation is the hot path, so default to a single-pass summary.
ENABLE_SUMMARY_QA = os.getenv("ENABLE_SUMMARY_QA", "false").lower() == "true"

MAX_FEATURED_PAPERS = int(os.getenv("MAX_FEATURED_PAPERS", "12"))
MAX_BRIEF_PAPERS = int(os.getenv("MAX_BRIEF_PAPERS", "13"))
PROCESS_ALL_WHEN_NO_NEW = os.getenv("PROCESS_ALL_WHEN_NO_NEW", "true").lower() == "true"

MAX_SECTION_CHARS = int(os.getenv("MAX_SECTION_CHARS", "5000"))
MAX_SUMMARY_CONTEXT_CHARS = int(os.getenv("MAX_SUMMARY_CONTEXT_CHARS", "6000"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "220"))
OLLAMA_FALLBACK_NUM_PREDICT = int(os.getenv("OLLAMA_FALLBACK_NUM_PREDICT", "140"))
