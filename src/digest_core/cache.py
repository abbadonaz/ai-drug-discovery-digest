from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

from digest_core.utils import load_json, save_json


@dataclass(frozen=True)
class CacheEntry:
    value: list[dict]
    created_at: datetime

    @property
    def is_available(self):
        return bool(self.value)


class JsonSourceCache:
    def __init__(self, cache_dir="data/source_cache"):
        self.cache_dir = Path(cache_dir)

    def get(self, key: str, ttl_hours: int | None = None) -> CacheEntry | None:
        payload = load_json(self.cache_dir / f"{key}.json", default={})
        if not isinstance(payload, dict) or "value" not in payload:
            return None

        try:
            created_at = datetime.fromisoformat(payload.get("created_at", ""))
        except ValueError:
            return None

        if ttl_hours is not None:
            expires_at = created_at + timedelta(hours=ttl_hours)
            if expires_at < datetime.now(timezone.utc):
                return None

        return CacheEntry(value=payload.get("value") or [], created_at=created_at)

    def get_stale(self, key: str) -> CacheEntry | None:
        return self.get(key, ttl_hours=None)

    def set(self, key: str, value: list[dict]):
        save_json(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "value": value,
            },
            self.cache_dir / f"{key}.json",
        )


def retry_call(func, attempts=2, base_delay_seconds=1.0):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as error:
            last_error = error
            if attempt >= attempts:
                break
            time.sleep(base_delay_seconds * attempt)

    raise last_error
