import ollama

TREND_PROMPT = """
You are writing the editorial introduction for a weekly digest
read by scientists working in:

- drug discovery
- cheminformatics
- computational chemistry
- molecular machine learning

Based on the paper summaries below, identify the **main research
themes emerging this week**.

Focus on:

• recurring methods or technologies  
• important trends in molecular AI or computational chemistry  
• why these developments matter for industrial R&D  

Write **3–4 concise sentences** that read like an editorial
introduction to the digest.

Rules:

- Do NOT mention paper titles
- Do NOT list papers
- Do NOT repeat sentences from the summaries
- Avoid generic phrases like "this week several papers"
- Focus on concrete scientific themes

Paper summaries:

{summaries}
"""

def build_trend_input(summaries):

    text = ""

    for paper in summaries:

        text += f"""
Topic: {paper['topic']}

Summary:
{paper['tldr']}

---
"""

    return text

import ollama

def generate_weekly_narrative(summaries):

    context = build_trend_input(summaries)

    prompt = TREND_PROMPT.format(summaries=context)

    response = ollama.chat(
        model="mistral",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response["message"]["content"]