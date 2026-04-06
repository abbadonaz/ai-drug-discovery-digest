import re


PROMPT_INJECTION_PATTERNS = [
    r"\bignore (all|any|previous|prior) instructions\b",
    r"\bsystem prompt\b",
    r"\bdeveloper message\b",
    r"\byou are chatgpt\b",
    r"\bdo not summarize\b",
    r"\binstead,?\s+(respond|output|print|reveal)\b",
    r"\bexfiltrat(e|ion)\b",
    r"\breveal\b.{0,40}\bprompt\b",
]


def is_suspicious_text(text):
    lowered = (text or "").lower()
    return any(re.search(pattern, lowered) for pattern in PROMPT_INJECTION_PATTERNS)


def sanitize_llm_input(text):
    sanitized_lines = []

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if is_suspicious_text(line):
            continue
        sanitized_lines.append(line)

    sanitized = "\n".join(sanitized_lines)
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized.strip()


def safe_source_block(text, max_chars=6000):
    sanitized = sanitize_llm_input(text)
    if len(sanitized) > max_chars:
        return sanitized[:max_chars]
    return sanitized
