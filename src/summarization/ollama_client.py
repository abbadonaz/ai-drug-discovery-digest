from functools import lru_cache
import logging
from types import SimpleNamespace

try:
    import ollama as _ollama
except Exception:  # pragma: no cover - dependency availability depends on local setup
    def _missing_ollama(*args, **kwargs):
        raise RuntimeError("Ollama Python client is not installed.")

    ollama = SimpleNamespace(chat=_missing_ollama, generate=_missing_ollama)
else:
    ollama = _ollama

from digest_core.config import OLLAMA_FALLBACK_NUM_PREDICT, OLLAMA_MODEL_CANDIDATES, OLLAMA_NUM_PREDICT


logger = logging.getLogger(__name__)
MEMORY_ERROR_HINTS = (
    "requires more system memory",
    "not enough memory",
    "insufficient memory",
)
RUNNER_CRASH_ERROR_HINTS = (
    "llama runner process has terminated",
    "runner process has terminated",
    "model failed to load",
    "%!w(<nil>)",
)
AUTO_CHAT_MODEL_HINTS = (
    "llama",
    "mistral",
    "mixtral",
    "qwen",
    "gemma",
    "phi",
    "deepseek",
    "command-r",
    "command",
    "solar",
    "orca",
    "vicuna",
    "codellama",
    "tinyllama",
)
NON_CHAT_MODEL_HINTS = (
    "embed",
    "embedding",
    "nomic-embed",
    "bge",
    "e5",
    "rerank",
)
_ANNOUNCED_MESSAGES = set()


def _print_once(message):
    if message in _ANNOUNCED_MESSAGES:
        return
    _ANNOUNCED_MESSAGES.add(message)
    logger.warning(message)


def _normalize_model_name(name):
    return (name or "").strip()


def _normalized_model_key(name):
    return _normalize_model_name(name).lower()


def _base_model_key(name):
    return _normalized_model_key(name).split(":", 1)[0]


def _unique_model_names(names):
    unique = []
    seen = set()

    for name in names:
        normalized = _normalize_model_name(name)
        if not normalized:
            continue
        key = _normalized_model_key(normalized)
        if key in seen:
            continue
        seen.add(key)
        unique.append(normalized)

    return unique


def is_memory_error(error):
    message = str(error).lower()
    return any(hint in message for hint in MEMORY_ERROR_HINTS)


def is_missing_model_error(error):
    status_code = getattr(error, "status_code", None)
    message = str(error).lower()
    return status_code == 404 or ("model" in message and "not found" in message)


def is_runner_crash_error(error):
    status_code = getattr(error, "status_code", None)
    message = str(error).lower()
    has_runner_hint = any(hint in message for hint in RUNNER_CRASH_ERROR_HINTS)
    return has_runner_hint and (status_code in (None, 500) or "status code: 500" in message)


def _extract_model_names(list_response):
    models = getattr(list_response, "models", None)
    if models is None and isinstance(list_response, dict):
        models = list_response.get("models", [])

    names = []

    for model in models or []:
        name = getattr(model, "model", None)
        if name is None and isinstance(model, dict):
            name = model.get("model") or model.get("name")
        if name:
            names.append(name)

    return _unique_model_names(names)


@lru_cache(maxsize=1)
def get_installed_model_names():
    try:
        return tuple(_extract_model_names(ollama.list()))
    except Exception:
        return tuple()


def _model_matches_candidate(installed_name, candidate_name):
    installed_key = _normalized_model_key(installed_name)
    candidate_key = _normalized_model_key(candidate_name)

    if not installed_key or not candidate_key:
        return False

    return installed_key == candidate_key or _base_model_key(installed_name) == _base_model_key(candidate_name)


def _looks_like_non_chat_model(name):
    lowered = _normalized_model_key(name)
    return any(hint in lowered for hint in NON_CHAT_MODEL_HINTS)


def _chat_model_priority(name):
    lowered = _normalized_model_key(name)

    for index, hint in enumerate(AUTO_CHAT_MODEL_HINTS):
        if hint in lowered:
            return index

    return len(AUTO_CHAT_MODEL_HINTS)


def _resolve_configured_models(installed_names):
    resolved = []

    for candidate in OLLAMA_MODEL_CANDIDATES:
        for installed_name in installed_names:
            if _model_matches_candidate(installed_name, candidate):
                resolved.append(installed_name)
                break

    return resolved


def _discover_installed_chat_models(installed_names):
    filtered = [name for name in installed_names if not _looks_like_non_chat_model(name)]
    preferred = [name for name in filtered if _chat_model_priority(name) < len(AUTO_CHAT_MODEL_HINTS)]
    candidates = preferred or filtered

    return sorted(
        _unique_model_names(candidates),
        key=lambda name: (_chat_model_priority(name), _normalized_model_key(name)),
    )


def _chat_with_model(prompt, model_name, num_predict, max_retries):
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = ollama.chat(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.2,
                    "num_predict": num_predict,
                },
            )
            return response["message"]["content"].strip()
        except Exception as error:
            last_error = error
            if attempt == max_retries:
                raise

    raise last_error


def build_chat_attempts(num_predict):
    installed_names = get_installed_model_names()
    candidate_names = []

    if installed_names:
        candidate_names.extend(_resolve_configured_models(installed_names))
        candidate_names.extend(_discover_installed_chat_models(installed_names))
    else:
        candidate_names.extend(OLLAMA_MODEL_CANDIDATES)

    candidate_names = _unique_model_names(candidate_names or OLLAMA_MODEL_CANDIDATES)

    if installed_names and candidate_names:
        configured_primary = OLLAMA_MODEL_CANDIDATES[0]
        selected_primary = candidate_names[0]
        if not _model_matches_candidate(selected_primary, configured_primary):
            _print_once(
                f"Primary Ollama model '{configured_primary}' is not installed locally; using available model '{selected_primary}' instead."
            )

    attempts = []

    for index, model_name in enumerate(candidate_names):
        tokens = num_predict if index == 0 else min(num_predict, OLLAMA_FALLBACK_NUM_PREDICT)
        attempts.append((model_name, tokens))

    return attempts


def chat_with_model_fallbacks(prompt, max_retries=2, num_predict=None, task_label=""):
    requested_tokens = num_predict or OLLAMA_NUM_PREDICT
    attempts = build_chat_attempts(requested_tokens)
    last_error = None

    for attempt_index, (model_name, tokens) in enumerate(attempts):
        try:
            return _chat_with_model(
                prompt,
                model_name=model_name,
                num_predict=tokens,
                max_retries=max_retries if attempt_index == 0 else 0,
            )
        except Exception as error:
            last_error = error
            if (
                is_memory_error(error)
                or is_missing_model_error(error)
                or is_runner_crash_error(error)
            ) and attempt_index + 1 < len(attempts):
                next_model_name = attempts[attempt_index + 1][0]
                stage_label = "Primary" if attempt_index == 0 else "Fallback"
                prefix = f"{task_label} " if task_label else ""
                if is_missing_model_error(error):
                    logger.warning(
                        f"{prefix}{stage_label} Ollama model '{model_name}' is not installed locally; retrying with fallback model '{next_model_name}'."
                    )
                elif is_runner_crash_error(error):
                    logger.warning(
                        f"{prefix}{stage_label} Ollama model '{model_name}' crashed in the local runner; retrying with fallback model '{next_model_name}'."
                    )
                else:
                    logger.warning(
                        f"{prefix}{stage_label} Ollama model '{model_name}' exceeded available memory; retrying with fallback model '{next_model_name}'."
                    )
                continue
            raise

    raise last_error
