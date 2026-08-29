import re


def split_claims(summary_text):
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", summary_text or "")
        if sentence.strip()
    ]


def normalize_evidence_items(evidence):
    normalized = []

    for index, item in enumerate(evidence or [], start=1):
        copied = dict(item)
        copied["evidence_id"] = copied.get("evidence_id") or f"E{index}"
        normalized.append(copied)

    return normalized


def build_summary_provenance(summary_text, evidence):
    evidence_items = normalize_evidence_items(evidence)
    claims = split_claims(summary_text)
    provenance = []

    for claim_index, claim in enumerate(claims, start=1):
        preferred_role = _preferred_summary_role(claim_index)
        matching = [
            item for item in evidence_items
            if item.get("summary_role") == preferred_role
        ]
        if not matching:
            matching = evidence_items[:2]

        provenance.append({
            "claim_id": f"C{claim_index}",
            "claim": claim,
            "evidence": [
                {
                    "evidence_id": item["evidence_id"],
                    "summary_role": item.get("summary_role", item.get("role", "supporting")),
                    "role": item.get("role", "supporting"),
                    "section": item.get("section", "unknown"),
                    "text": item.get("text", ""),
                    "score": item.get("score", 0),
                }
                for item in matching[:2]
            ],
        })

    return provenance


def _preferred_summary_role(claim_index):
    if claim_index == 1:
        return "overview"
    if claim_index == 2:
        return "result"
    return "approach"
