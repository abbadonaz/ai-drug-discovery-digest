from digest_core.config import (
    MAX_NARRATIVE_CONTEXT_CHARS,
    MAX_NARRATIVE_PAPERS,
    MAX_NARRATIVE_SUMMARY_CHARS,
    OLLAMA_FALLBACK_NUM_PREDICT,
    OLLAMA_NUM_PREDICT,
)
import logging
from summarization.ollama_client import chat_with_model_fallbacks, ollama
from evidence.security import safe_source_block


TREND_PROMPT = """
You are writing the editorial introduction for a weekly digest read by scientists working in:

- drug discovery
- cheminformatics
- computational chemistry
- generative chemistry
- QSAR and ADMET
- molecular machine learning

Based on the paper summaries below, identify the main research themes emerging this week.

Focus on:
- recurring methods or technologies
- important trends in molecular AI or computational chemistry
- why these developments matter for industrial R&D

Write 3-4 concise sentences that read like an editorial introduction to the digest.

Rules:
- Do not mention paper titles
- Do not list papers
- Do not repeat sentences from the summaries
- Avoid generic phrases like "this week several papers"
- Focus on concrete scientific themes

Paper summaries:

{summaries}
"""
logger = logging.getLogger(__name__)


def build_trend_input(summaries):
    chunks = []
    used_chars = 0
    separator = "\n---\n"

    for paper in summaries[:MAX_NARRATIVE_PAPERS]:
        remaining_budget = MAX_NARRATIVE_CONTEXT_CHARS - used_chars
        if chunks:
            remaining_budget -= len(separator)
        if remaining_budget <= 0:
            break

        prefix = f"Topic: {paper.get('topic', 'Other')}\n\nSummary:\n"
        summary_budget = min(
            MAX_NARRATIVE_SUMMARY_CHARS,
            max(remaining_budget - len(prefix) - 1, 0),
        )
        if summary_budget < 120:
            break

        summary = safe_source_block(paper.get("tldr", ""), max_chars=summary_budget)
        if not summary:
            continue

        chunk = f"{prefix}{summary}\n"
        if chunks:
            used_chars += len(separator)
        chunks.append(chunk)
        used_chars += len(chunk)

    return separator.join(chunks)


def generate_weekly_narrative(summaries):
    featured = [paper for paper in summaries if not paper.get("brief", False)]
    if not featured:
        return "This digest collected relevant literature, but no full featured summaries were available for narrative synthesis."

    context = build_trend_input(featured)
    if not context:
        return "This week's set of papers spans molecular AI, computational chemistry, and decision-support methods for drug discovery."

    prompt = TREND_PROMPT.format(summaries=context)

    try:
        return chat_with_model_fallbacks(
            prompt,
            max_retries=0,
            num_predict=min(OLLAMA_NUM_PREDICT, OLLAMA_FALLBACK_NUM_PREDICT + 40),
            task_label="Weekly narrative",
        )
    except Exception as error:
        logger.warning("Weekly narrative generation failed: %s", error)
        return "This week's featured papers emphasize practical model evaluation, better scientific evidence selection, and methods that may improve decision-making in drug discovery workflows."
