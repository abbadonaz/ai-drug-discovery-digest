import ollama


MODEL_NAME = "mistral"


PROMPT_TEMPLATE = """
You are writing a short research briefing for scientists working in
drug discovery, cheminformatics and molecular machine learning.

Use ONLY the information provided below.
Do NOT invent facts.

Write the summary in **Markdown format** using the exact structure below.

### Problem
1-2 sentences explaining the scientific problem.

### Method
1-2 sentences explaining the proposed method or model.

### Dataset / Benchmark
1 sentence describing the dataset, benchmark, or evaluation setup.

### Key Findings
Write 2-3 bullet points using this format:

- finding one
- finding two
- finding three

### Why It Matters
1-2 sentences explaining why the work matters for drug discovery,
computational chemistry, or molecular machine learning.

Important rules:
- Maximum 180 words
- Use clear scientific language
- Do not repeat the paper title
- Do not speculate beyond the provided text
- Always keep bullet points on separate lines

Paper excerpts:

{sentences}
"""

def truncate_text(text, max_chars=8000):
    """
    Prevent sending extremely large prompts to the LLM.
    """
    if len(text) > max_chars:
        return text[:max_chars]
    return text

def summarize_with_llm(sentences):

    text_block = "\n".join(sentences)
    text_block = truncate_text(text_block)

    prompt = PROMPT_TEMPLATE.format(sentences=text_block)

    try:

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )

        return response["message"]["content"]

    except Exception as e:

        print("LLM error, retrying once...")

        try:

            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}]
            )

            return response["message"]["content"]

        except Exception:

            print("LLM failed, returning fallback summary")

            return "Summary generation failed due to model error."


def summarize_papers(papers):

    summaries = []

    for paper in papers:

        print(f"Summarizing: {paper['title']}")

        summary_text = summarize_with_llm(paper["sentences"])

        summaries.append({
            "title": paper["title"],
            "url": paper["url"],
            "topic": paper.get("topic", "Other"),
            "tldr": summary_text
        })

    return summaries