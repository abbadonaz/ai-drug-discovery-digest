from collections import defaultdict
import markdown
import re


def clean_llm_output(text):
    """
    Fix common LLM formatting issues before rendering markdown.
    """

    if not text:
        return ""

    # Normalize bullet formatting
    text = re.sub(r"\s*-\s*", "\n- ", text)

    # Ensure spacing before sections
    sections = [
        "Problem",
        "Method",
        "Dataset / Benchmark",
        "Key Findings",
        "Why It Matters"
    ]

    for s in sections:
        text = re.sub(rf"\s*{s}\s*", f"\n\n**{s}**\n", text)

    return text.strip()


def render_markdown(text):
    """
    Convert LLM markdown summaries to HTML.
    """

    text = clean_llm_output(text)

    return markdown.markdown(
        text,
        extensions=[
            "extra",
            "sane_lists"
        ]
    )


def generate_digest_html(summaries, narrative):

    html = ""

    # ----------------------------
    # Paper of the Week
    # ----------------------------

    if summaries:

        top = summaries[0]

        summary_html = render_markdown(top["tldr"])

        html += f"""
        <div class="hero">

            <h2>⭐ Paper of the Week</h2>

            <div class="paper-title">{top['title']}</div>

            <div class="meta">
            Area: {top['topic']}
            </div>

            <div class="summary">
            {summary_html}
            </div>

            <a href="{top['url']}">Read the paper →</a>

        </div>
        """

    # ----------------------------
    # Weekly Trend Narrative
    # ----------------------------

    narrative_html = render_markdown(narrative)

    html += f"""
    <div class="trend">

        <h2>☕ Trend of the Week</h2>

        <div class="summary">
        {narrative_html}
        </div>

    </div>
    """

    # ----------------------------
    # Group Papers by Topic
    # ----------------------------

    groups = defaultdict(list)

    for paper in summaries[1:]:
        groups[paper["topic"]].append(paper)

    # ----------------------------
    # Topic Sections
    # ----------------------------

    for topic, papers in groups.items():

        html += f"""
        <div class='section-title'>
        {topic}
        </div>
        """

        for paper in papers:

            summary_html = render_markdown(paper["tldr"])

            html += f"""
            <div class="paper-card">

                <div class="paper-title">
                {paper['title']}
                </div>

                <div class="meta">
                Area: {paper['topic']}
                </div>

                <div class="summary">
                {summary_html}
                </div>

                <a href="{paper['url']}">Read paper →</a>

            </div>
            """

    return html