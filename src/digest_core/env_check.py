import importlib.util
import json
import sys


REQUIRED_IMPORTS = {
    "arxiv": "arxiv",
    "Bio": "biopython",
    "feedparser": "feedparser",
    "markdown": "markdown",
    "numpy": "numpy",
    "ollama": "ollama",
    "pdfminer": "pdfminer.six",
    "pydantic": "pydantic",
    "requests": "requests",
    "sklearn": "scikit-learn",
    "sentence_transformers": "sentence-transformers",
    "torch": "torch",
}


def check_environment():
    missing = [
        package
        for import_name, package in REQUIRED_IMPORTS.items()
        if importlib.util.find_spec(import_name) is None
    ]

    return {
        "python": sys.version.split()[0],
        "ok": not missing,
        "missing": missing,
        "setup": [
            "uv venv",
            "uv sync --extra dev",
            "uv run digest-check-env",
            "uv run digest-run",
        ],
    }


def main():
    result = check_environment()
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
