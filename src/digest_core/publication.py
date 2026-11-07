"""Lightweight artifact validation and current-run deployment gate."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_artifact(path: Path, text: str):
    if path.suffix == ".json":
        json.loads(text)
    elif path.suffix == ".html":
        lowered = text.lower()
        if not all(token in lowered for token in ("<html", "<body", "</body>", "</html>")):
            raise ValueError(f"Incomplete HTML: {path}")
        HTMLParser().feed(text)
    else:
        raise ValueError(f"Unexpected publication artifact: {path}")


def verify_manifest(path, expected_run_id):
    path = Path(path)
    if (path.parent / ".publication.lock").exists():
        raise ValueError("Publication lock exists; run or recovery is incomplete")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not expected_run_id or manifest.get("run_id") != expected_run_id or manifest.get("status") != "published":
        raise ValueError("No completed publication for this run")
    artifacts = manifest["artifacts"]
    if not {"post", "index", "archive", "summaries"}.issubset({entry["role"] for entry in artifacts}):
        raise ValueError("Required publication artifacts are missing")
    for entry in artifacts:
        artifact = path.parent / entry["path"]
        content = artifact.read_bytes()
        if content_hash(content) != entry["sha256"]:
            raise ValueError(f"Publication checksum mismatch: {artifact}")
        validate_artifact(artifact, content.decode("utf-8"))
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Verify the current publication before deployment")
    parser.add_argument("--manifest", default="docs/publication.json")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    verify_manifest(args.manifest, args.run_id)
    print("Current publication manifest and artifact checksums verified")


if __name__ == "__main__":
    main()
