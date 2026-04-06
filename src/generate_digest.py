from collections import defaultdict
from html import escape
import re

import markdown


def clean_llm_output(text):
    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    headings = [
        "Problem",
        "Method",
        "Dataset / Benchmark",
        "Key Findings",
        "Why It Matters",
    ]
    for heading in headings:
        text = re.sub(
            rf"(?:^|\n)\s*#+\s*{re.escape(heading)}\s*",
            f"\n\n### {heading}\n",
            text,
            flags=re.IGNORECASE,
        )

    return text.strip()


def render_markdown(text):
    cleaned = clean_llm_output(text)
    if not cleaned:
        return "<p>No summary available.</p>"
    return markdown.markdown(cleaned, extensions=["extra", "sane_lists"])


def _render_topic_badges(summary_count, brief_count):
    return f"""
    <div class="digest-stats">
        <div class="stat-card">
            <span class="stat-value">{summary_count}</span>
            <span class="stat-label">Featured papers</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">{brief_count}</span>
            <span class="stat-label">Additional references</span>
        </div>
    </div>
    """


def generate_digest_html(summaries, narrative):
    featured = [paper for paper in summaries if not paper.get("brief", False)]
    brief = [paper for paper in summaries if paper.get("brief", False)]

    html = _render_topic_badges(len(featured), len(brief))

    if featured:
        top = featured[0]
        html += f"""
        <section class="must-read-container">
            <div class="must-read-badge">Editor's pick</div>
            <article class="must-read-paper">
                <div class="must-read-meta">
                    <span class="topic-badge">{escape(top.get('topic', 'Other'))}</span>
                    <span class="rank-indicator">Highest ranked paper this week</span>
                </div>
                <h2 class="must-read-title">{escape(top['title'])}</h2>
                <div class="must-read-summary">
                    {render_markdown(top.get("tldr", ""))}
                </div>
                <div class="must-read-action">
                    <a href="{escape(top['url'])}" class="btn-primary">Read the paper</a>
                    <a href="{escape(top['url'])}" class="btn-secondary">Open source record</a>
                </div>
            </article>
        </section>
        """

    html += f"""
    <section class="insights-container">
        <h2 class="section-headline">Weekly research themes</h2>
        <p class="section-subtitle">A short editorial synthesis of the strongest scientific directions in this batch.</p>
        <div class="insights-body">
            {render_markdown(narrative)}
        </div>
    </section>
    """

    if len(featured) > 1:
        html += """
        <section class="featured-section">
            <h2 class="section-headline">Featured papers</h2>
            <p class="section-subtitle">Structured summaries for the most relevant papers after retrieval, filtering, and evidence selection.</p>
        """

        groups = defaultdict(list)
        for paper in featured[1:]:
            groups[paper.get("topic", "Other")].append(paper)

        global_rank = 2
        for topic, papers in sorted(groups.items()):
            html += f"""
            <div class="topic-group">
                <h3 class="topic-header">{escape(topic)}</h3>
                <div class="papers-grid">
            """

            for paper in papers:
                html += f"""
                <article class="paper-card-featured">
                    <div class="paper-rank">#{global_rank}</div>
                    <h4 class="paper-title-featured">{escape(paper['title'])}</h4>
                    <div class="paper-summary-featured">
                        {render_markdown(paper.get("tldr", ""))}
                    </div>
                    <div class="paper-footer">
                        <a href="{escape(paper['url'])}" class="link-read-more">Read paper</a>
                    </div>
                </article>
                """
                global_rank += 1

            html += """
                </div>
            </div>
            """

        html += "</section>"

    if brief:
        html += f"""
        <section class="optional-section">
            <h2 class="section-headline">Additional references</h2>
            <p class="section-subtitle">{len(brief)} papers passed the filter but were not expanded into full summaries.</p>
            <div class="brief-list">
        """

        brief_groups = defaultdict(list)
        for paper in brief:
            brief_groups[paper.get("topic", "Other")].append(paper)

        for topic, papers in sorted(brief_groups.items()):
            html += f"<div class='brief-topic'><h4 class='brief-topic-title'>{escape(topic)}</h4>"
            for paper in papers:
                html += f"""
                <div class="brief-item">
                    <a href="{escape(paper['url'])}" class="brief-link">{escape(paper['title'])}</a>
                </div>
                """
            html += "</div>"

        html += """
            </div>
        </section>
        """

    return html
