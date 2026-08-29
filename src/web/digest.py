from collections import defaultdict
from html import escape
import re

import markdown


def clean_llm_output(text):
    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s*\[E\d+\]", "", text)
    text = re.sub(r"\bThe paper\s+\"([^\"]+)\"\s+", "", text)
    text = re.sub(r"\bThis paper\s+\"([^\"]+)\"\s+", "", text)

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
    return markdown.markdown(escape(cleaned), extensions=["extra", "sane_lists"])


def slugify_title(title):
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return slug or "paper"


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


def _score_label(value):
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _cluster_name(paper):
    return paper.get("cluster_label") or paper.get("topic", "Other")


def _paper_metric(paper, key):
    return _score_label(paper.get(key))


def _render_research_brief(featured, brief):
    if not featured and not brief:
        return ""

    topics = defaultdict(int)
    clusters = defaultdict(int)
    for paper in featured + brief:
        topics[paper.get("topic", "Other")] += 1
        clusters[_cluster_name(paper)] += 1

    top_topics = sorted(topics.items(), key=lambda item: item[1], reverse=True)[:4]
    top_clusters = sorted(clusters.items(), key=lambda item: item[1], reverse=True)[:4]

    topic_items = "".join(
        f"<li><strong>{escape(topic)}</strong><span>{count} paper(s)</span></li>"
        for topic, count in top_topics
    )
    cluster_items = "".join(
        f"<li><strong>{escape(cluster)}</strong><span>{count} representative/reference paper(s)</span></li>"
        for cluster, count in top_clusters
    )

    return f"""
    <section class="briefing-panel">
        <div>
            <h2 class="section-headline">Research brief</h2>
            <p class="section-subtitle">A compact orientation layer for scanning the week before opening individual papers.</p>
        </div>
        <div class="briefing-grid">
            <div class="briefing-block">
                <h3>Dominant topics</h3>
                <ul class="signal-list">{topic_items}</ul>
            </div>
            <div class="briefing-block">
                <h3>Active clusters</h3>
                <ul class="signal-list">{cluster_items}</ul>
            </div>
        </div>
    </section>
    """


def _render_cluster_map(featured):
    clusters = defaultdict(list)
    for paper in featured:
        cluster_label = paper.get("cluster_label")
        if cluster_label:
            clusters[cluster_label].append(paper)

    if not clusters:
        return ""

    html = """
    <section class="comparison-section">
        <h2 class="section-headline">Weekly literature map</h2>
        <p class="section-subtitle">Featured papers are selected as representatives of the strongest clusters in this batch.</p>
        <div class="cluster-grid">
    """

    for label, papers in sorted(clusters.items()):
        overview = papers[0].get("cluster_overview") or f"{label} includes {len(papers)} selected representative paper(s)."
        html += f"""
        <div class="cluster-row">
            <div>
                <h3>{escape(label)}</h3>
                <p>{escape(overview)}</p>
            </div>
            <span>{len(papers)} selected</span>
        </div>
        """

    html += """
        </div>
    </section>
    """
    return html


def _render_comparison_table(featured):
    if not featured:
        return ""

    rows = ""
    for index, paper in enumerate(featured, start=1):
        rows += f"""
        <tr>
            <td>{index}</td>
            <td><a href="#{slugify_title(paper['title'])}">{escape(paper['title'])}</a></td>
            <td>{escape(paper.get('topic', 'Other'))}</td>
            <td>{escape(_cluster_name(paper))}</td>
            <td>{_paper_metric(paper, 'score')}</td>
        </tr>
        """

    return f"""
    <section class="comparison-section">
        <h2 class="section-headline">At-a-glance comparison</h2>
        <p class="section-subtitle">Use this table to compare topic fit, cluster context, final digest priority, and representative selection strength.</p>
        <div class="table-wrap">
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Paper</th>
                        <th>Topic</th>
                        <th>Cluster</th>
                        <th>Digest score</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </section>
    """


def _render_provenance(paper):
    provenance = paper.get("provenance") or []
    if not provenance:
        return ""

    items = ""
    for claim in provenance[:2]:
        evidence = claim.get("evidence") or []
        evidence_lines = "".join(
            f"<li><span>{escape(item.get('section', 'evidence'))}</span>{escape(item.get('text', ''))}</li>"
            for item in evidence[:2]
            if item.get("text")
        )
        if not evidence_lines:
            continue
        items += f"""
        <details class="evidence-detail">
            <summary>{escape(claim.get("claim", "Evidence"))}</summary>
            <ul>{evidence_lines}</ul>
        </details>
        """

    if not items:
        return ""

    return f"""
    <div class="evidence-box">
        <h5>Evidence trace</h5>
        {items}
    </div>
    """


def _render_topic_card(paper, rank):
    paper_slug = slugify_title(paper["title"])
    return f"""
    <article class="paper-card-featured" id="{paper_slug}">
        <div class="paper-rank">#{rank}</div>
        <h4 class="paper-title-featured">{escape(paper['title'])}</h4>
        <div class="paper-meta-line">
            <span>{escape(_cluster_name(paper))}</span>
            <span>digest {_paper_metric(paper, 'score')}</span>
            <span>selection {_paper_metric(paper, 'selection_score')}</span>
        </div>
        <div class="paper-summary-featured">
            {render_markdown(paper.get("tldr", ""))}
        </div>
        {_render_provenance(paper)}
        <div class="paper-footer">
            <a href="{escape(paper['url'])}" class="link-read-more">Read paper</a>
        </div>
    </article>
    """


def _render_reference_list(papers):
    if not papers:
        return "<p class=\"section-subtitle\">No lightweight references for this topic.</p>"

    links = ""
    for paper in papers:
        links += f"""
        <div class="brief-item">
            <a href="{escape(paper['url'])}" class="brief-link">{escape(paper['title'])}</a>
        </div>
        """

    return f"<div class=\"brief-list compact-reference-list\">{links}</div>"


def _render_topic_tabs(featured, brief):
    topic_names = sorted({
        paper.get("topic", "Other")
        for paper in featured + brief
    })
    if not topic_names:
        return ""

    featured_ranks = {
        paper["url"]: index
        for index, paper in enumerate(featured, start=1)
    }

    controls = ""
    panels = ""
    group_id = "topic-tabs"

    for index, topic in enumerate(topic_names):
        tab_id = f"topic-tab-{index}"
        panel_id = f"topic-panel-{index}"
        topic_featured = [paper for paper in featured if paper.get("topic", "Other") == topic]
        topic_brief = [paper for paper in brief if paper.get("topic", "Other") == topic]
        checked = " checked" if index == 0 else ""

        controls += f"""
        <input class="topic-tab-input" type="radio" name="{group_id}" id="{tab_id}" aria-controls="{panel_id}"{checked}>
        <label class="topic-tab-label" for="{tab_id}">
            <span>{escape(topic)}</span>
            <strong>{len(topic_featured)} + {len(topic_brief)}</strong>
        </label>
        """

        featured_cards = "".join(
            _render_topic_card(paper, featured_ranks[paper["url"]])
            for paper in topic_featured
        )

        panels += f"""
        <section class="topic-tab-panel" id="{panel_id}">
            <div class="topic-panel-header">
                <div>
                    <h3>{escape(topic)}</h3>
                    <p>{len(topic_featured)} featured summary paper(s), {len(topic_brief)} additional reference(s).</p>
                </div>
                <span>{len(topic_featured) + len(topic_brief)} total</span>
            </div>
            <div class="topic-panel-grid">
                <div>
                    <h4>Featured analysis</h4>
                    <div class="papers-grid">
                        {featured_cards or '<p class="section-subtitle">No expanded summaries for this topic.</p>'}
                    </div>
                </div>
                <aside class="topic-reference-panel">
                    <h4>Additional references</h4>
                    {_render_reference_list(topic_brief)}
                </aside>
            </div>
        </section>
        """

    return f"""
    <section class="topic-tabs-section">
        <div class="topic-tabs-header">
            <h2 class="section-headline">Explore by research category</h2>
            <p class="section-subtitle">Switch categories to compare expanded summaries, cluster context, and additional references without losing the weekly overview.</p>
        </div>
        <div class="topic-tabs">
            <div class="topic-tab-controls">{controls}</div>
            <div class="topic-tab-panels">{panels}</div>
        </div>
    </section>
    """


def generate_digest_html(summaries, narrative):
    featured = [paper for paper in summaries if not paper.get("brief", False)]
    brief = [paper for paper in summaries if paper.get("brief", False)]

    html = _render_topic_badges(len(featured), len(brief))
    html += _render_research_brief(featured, brief)
    html += _render_cluster_map(featured)
    html += _render_comparison_table(featured)

    html += f"""
    <section class="insights-container">
        <h2 class="section-headline">Weekly research themes</h2>
        <p class="section-subtitle">A short editorial synthesis of the strongest scientific directions in this batch.</p>
        <div class="insights-body">
            {render_markdown(narrative)}
        </div>
    </section>
    """

    html += _render_topic_tabs(featured, brief)

    return html
