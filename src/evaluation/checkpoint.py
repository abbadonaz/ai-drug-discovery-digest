"""Immutable replay checkpoints; raw responses survive parsing failures."""
from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from digest_core.atomic import stage_bytes
from summarization.ollama_client import ChatText


def write_once(path: Path, value: object) -> None:
    """Publish a complete JSON file without replacing any existing checkpoint."""
    staged = stage_bytes(path, json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8"))
    try:
        os.link(staged, path)
    finally:
        staged.unlink(missing_ok=True)


@contextmanager
def replay_lock(output: Path):
    """A stale lock requires inspection; never silently steal another replay."""
    output.mkdir(parents=True, exist_ok=True)
    path = output / ".replay.lock"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    try:
        yield
    finally:
        path.unlink()


class CheckpointChat:
    def __init__(self, prefix: Path, model: str, tokens: int, chat):
        self.prefix, self.model, self.tokens, self.chat = prefix, model, tokens, chat
        self.calls: list[dict] = []
        self.failure: Exception | None = None

    def __call__(self, prompt: str, **kwargs) -> ChatText:
        if self.failure is not None:
            raise self.failure
        if self.calls:
            raise ValueError("One generation per condition; inspect the saved response before another prompt")
        digest = hashlib.sha256(prompt.encode()).hexdigest()
        path = self.prefix.with_name(self.prefix.name + f"-response-{digest}.json")
        if list(self.prefix.parent.glob(self.prefix.name + "-failure-*.json")):
            raise RuntimeError("Previous failure checkpoint exists; inspect it before explicitly retrying")
        parameters = {"temperature": .2, "num_predict": self.tokens}
        started = datetime.now(timezone.utc).isoformat()
        clock = time.perf_counter()
        try:
            if path.exists():
                record = json.loads(path.read_text(encoding="utf-8"))
                if (record["requested_model"] != self.model or record["parameters"] != parameters
                        or record["prompt_sha256"] != digest or record["prompt"] != prompt):
                    raise ValueError("Checkpoint generation settings differ")
            else:
                response = self.chat(model=self.model, messages=[{"role": "user", "content": prompt}], options=parameters)
                record = {"requested_model": self.model, "model": response.get("model") or self.model,
                          "parameters": parameters, "prompt": prompt, "prompt_sha256": digest,
                          "started_at": started, "elapsed_seconds": time.perf_counter() - clock,
                          "response": response["message"]["content"].strip(),
                          "ollama_metadata": {key: response.get(key) for key in (
                              "done", "done_reason", "total_duration", "load_duration",
                              "prompt_eval_count", "eval_count", "prompt_eval_duration", "eval_duration")}}
                write_once(path, record)
            self.calls.append({key: value for key, value in record.items() if key not in {"prompt", "response"}})
            return ChatText(record["response"], record["model"], parameters)
        except Exception as error:
            self.failure = error
            write_once(self.prefix.with_name(self.prefix.name + f"-failure-{uuid.uuid4().hex}.json"), {
                "recorded_at": datetime.now(timezone.utc).isoformat(), "error_type": type(error).__name__,
                "started_at": started, "elapsed_seconds": time.perf_counter() - clock,
                "status_code": getattr(error, "status_code", None), "message": str(error),
                "prompt": prompt, "prompt_sha256": digest, "model": self.model, "parameters": parameters})
            raise
