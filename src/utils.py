import json
from pathlib import Path


def save_json(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_json(path):
    with open(path) as f:
        return json.load(f)