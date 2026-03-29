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

SECTION_SUMMARY_PROMPT = """
You are summarizing a section of a scientific paper for domain experts in drug discovery.
Focus on one compact summary for this section: include key purpose and the main result if present.
Use markdown bullets or short sentences (<= 90 words).

Section: {section_name}

{section_text}
"""

QA_PROMPT = """
You are performing a consistency and hallucination check for a scientific summary.
Given the source text and the proposed summary, answer with:
- "VALID" if all claims are supported by source text
- "POTENTIAL_HALLUCINATION" if some claims cannot be confirmed, then list those claims.

Source Text:
{source_text}

Summary:
{summary_text}
"""


def truncate_text(text, max_chars=8000):
    if len(text) > max_chars:
        return text[:max_chars]
    return text


def summarize_section(section_name, section_text):
    content = SECTION_SUMMARY_PROMPT.format(section_name=section_name, section_text=truncate_text(section_text, 3800))

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": content}],
    )

    return response["message"]["content"].strip()


def hallucination_check(summary_text, source_text):
    content = QA_PROMPT.format(
        source_text=truncate_text(source_text, 7000),
        summary_text=truncate_text(summary_text, 2000),
    )

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": content}],
    )

    return response["message"]["content"].strip()


def summarize_with_llm(sentences):
    text_block = "\n".join(sentences)
    text_block = truncate_text(text_block)

    prompt = PROMPT_TEMPLATE.format(sentences=text_block)

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )

    return response["message"]["content"].strip()


def summarize_paper_two_stage(paper):
    section_summaries = []

    for section_name, section_text in (paper.get("sections") or {}).items():
        if not section_text:
            continue

        try:
            section_summary = summarize_section(section_name, section_text)
            section_summaries.append(f"### {section_name.title()}\n" + section_summary)
        except Exception as e:
            print(f"Section summarization failed for {paper['title']}:{section_name}, error: {e}")

    if section_summaries:
        stage_text = "\n\n".join(section_summaries)
    else:
        stage_text = "\n".join(paper.get("sentences", []))

    setting_text = []
    if paper.get("sentences"):
        setting_text.extend(paper["sentences"][:20])

    if section_summaries:
        setting_text.append("\n## Section-level summaries:\n")
        setting_text.extend(section_summaries)

    final_input = setting_text if setting_text else [stage_text]

    full_summary = summarize_with_llm(final_input)

    check_result = hallucination_check(full_summary, paper.get("context", ""))

    if "POTENTIAL_HALLUCINATION" in check_result.upper():
        warning_note = "\n> **QA warning**: potential hallucinations detected. Please verify claims against source text.\n"
    else:
        warning_note = ""

    return f"{full_summary}{warning_note}"


def summarize_papers(papers):
    summaries = []

    for paper in papers:
        print(f"Summarizing: {paper['title']}")

        try:
            summary_text = summarize_paper_two_stage(paper)
        except Exception as e:
            print(f"Two-stage summarization failed for {paper['title']}: {e}")
            summary_text = summarize_with_llm(paper.get("sentences", []))

        summaries.append({
            "title": paper["title"],
            "url": paper["url"],
            "topic": paper.get("topic", "Other"),
            "tldr": summary_text,
        })

    return summaries
