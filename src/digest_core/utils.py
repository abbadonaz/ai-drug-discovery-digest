import json
from pathlib import Path


def save_json(data, path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path, default=None):
    target = Path(path)
    fallback = [] if default is None else default

    if not target.exists():
        return fallback

    try:
        raw_text = target.read_text(encoding="utf-8")
    except OSError:
        return fallback

    if not raw_text.strip():
        return fallback

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        backup = target.with_suffix(target.suffix + ".corrupt")
        try:
            backup.write_text(raw_text, encoding="utf-8")
        except OSError:
            pass
        return fallback
