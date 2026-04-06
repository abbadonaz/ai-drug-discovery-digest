import ollama

from config import MODEL_NAME
from security import safe_source_block


TREND_PROMPT = """
You are writing the editorial introduction for a weekly digest read by scientists working in:

- drug discovery
- cheminformatics
- computational chemistry
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


def build_trend_input(summaries):
    chunks = []

    for paper in summaries:
        summary = safe_source_block(paper.get("tldr", ""), max_chars=1200)
        if not summary:
            continue

        chunks.append(
            f"Topic: {paper.get('topic', 'Other')}\n\nSummary:\n{summary}\n"
        )

    return "\n---\n".join(chunks)


def generate_weekly_narrative(summaries):
    featured = [paper for paper in summaries if not paper.get("brief", False)]
    if not featured:
        return "This digest collected relevant literature, but no full featured summaries were available for narrative synthesis."

    context = build_trend_input(featured)
    if not context:
        return "This week's set of papers spans molecular AI, computational chemistry, and decision-support methods for drug discovery."

    prompt = TREND_PROMPT.format(summaries=context)

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"].strip()
    except Exception as error:
        print(f"Weekly narrative generation failed: {error}")
        return "This week's featured papers emphasize practical model evaluation, better scientific evidence selection, and methods that may improve decision-making in drug discovery workflows."
