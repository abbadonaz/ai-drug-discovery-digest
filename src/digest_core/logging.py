from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import time
import uuid


@dataclass
class StageTimer:
    name: str
    logger: "RunLogger"
    started_at: float = field(default_factory=time.perf_counter)

    def finish(self, **fields):
        elapsed_ms = round((time.perf_counter() - self.started_at) * 1000, 2)
        self.logger.info(self.name, "finished", elapsed_ms=elapsed_ms, **fields)


class RunLogger:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or uuid.uuid4().hex[:12]

    def timer(self, stage: str) -> StageTimer:
        self.info(stage, "started")
        return StageTimer(stage, self)

    def info(self, stage: str, event: str, **fields):
        self._emit("info", stage, event, fields)

    def warning(self, stage: str, event: str, **fields):
        self._emit("warning", stage, event, fields)

    def error(self, stage: str, event: str, **fields):
        self._emit("error", stage, event, fields)

    def _emit(self, level: str, stage: str, event: str, fields: dict):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "level": level,
            "stage": stage,
            "event": event,
        }
        payload.update(fields)
        print(json.dumps(payload, ensure_ascii=False, default=str))


class NullRunLogger:
    def timer(self, stage: str):
        return StageTimer(stage, self)

    def info(self, stage: str, event: str, **fields):
        return None

    def warning(self, stage: str, event: str, **fields):
        return None

    def error(self, stage: str, event: str, **fields):
        return None
