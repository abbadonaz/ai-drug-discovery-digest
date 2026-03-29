from collections import defaultdict
import markdown
import re


def clean_llm_output(text):
    """Fix common LLM formatting issues before rendering markdown."""
    if not text:
        return ""

    text = re.sub(r"\s*-\s*", "\n- ", text)

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
    """Convert LLM markdown to HTML."""
    text = clean_llm_output(text)
    return markdown.markdown(text, extensions=["extra", "sane_lists"])


def generate_digest_html(summaries, narrative):
    """Render digest with 1 'Must Read' + 11 featured + optionals."""
    html = ""

    # Separate featured from brief articles
    featured = [s for s in summaries if not s.get("brief", False)]
    brief = [s for s in summaries if s.get("brief", False)]

    # ----------------------------
    # MUST READ (Top paper, highly prominent)
    # ----------------------------
    
    must_read_badge = """
    <div class="must-read-badge">
        <span class="badge-icon">🎯</span>
        <span class="badge-text">MUST READ THIS WEEK</span>
    </div>
    """

    if featured:
        top = featured[0]
        summary_html = render_markdown(top["tldr"])

        html += f"""
        <div class="must-read-container">
            {must_read_badge}
            <div class="must-read-paper">
                <h1 class="must-read-title">{top['title']}</h1>
                
                <div class="must-read-meta">
                    <span class="topic-badge">{top['topic']}</span>
                    <span class="rank-indicator">Ranked #1 this week</span>
                </div>
                
                <div class="must-read-summary">
                    {summary_html}
                </div>
                
                <div class="must-read-action">
                    <a href="{top['url']}" class="btn-primary">Read Full Paper</a>
                    <a href="{top['url']}" class="btn-secondary">Open in arXiv/PubMed</a>
                </div>
            </div>
        </div>
        """

    # ----------------------------
    # Weekly Insights (Trend Narrative)
    # ----------------------------

    narrative_html = render_markdown(narrative)

    html += f"""
    <div class="insights-container">
        <h2 class="section-headline">📊 This Week's Insights</h2>
        <div class="insights-body">
            {narrative_html}
        </div>
    </div>
    """

    # ----------------------------
    # 11 Additional Featured Summaries (organized by topic)
    # ----------------------------

    if len(featured) > 1:
        featured_rest = featured[1:12]  # 11 additional papers
        
        html += """
        <div class="featured-section">
            <h2 class="section-headline">📖 Featured This Week</h2>
            <p class="section-subtitle">11 carefully selected papers advancing drug discovery and computational chemistry</p>
        """

        groups = defaultdict(list)
        for paper in featured_rest:
            groups[paper["topic"]].append(paper)

        for topic, papers in sorted(groups.items()):
            html += f"""
            <div class="topic-group">
                <h3 class="topic-header">{topic}</h3>
                <div class="papers-grid">
            """

            for idx, paper in enumerate(papers, 1):
                summary_html = render_markdown(paper["tldr"])
                
                html += f"""
                <div class="paper-card-featured">
                    <div class="paper-rank">#{idx + 1}</div>
                    
                    <h4 class="paper-title-featured">{paper['title']}</h4>
                    
                    <div class="paper-summary-featured">
                        {summary_html}
                    </div>
                    
                    <div class="paper-footer">
                        <a href="{paper['url']}" class="link-read-more">Read paper</a>
                    </div>
                </div>
                """

            html += """
                </div>
            </div>
            """

        html += "</div>"

    # ----------------------------
    # Optional Brief References
    # ----------------------------

    if brief:
        html += f"""
        <div class="optional-section">
            <h2 class="section-headline">🔗 Other Relevant Papers</h2>
            <p class="section-subtitle">Quick references to {len(brief)} additional papers that may be of interest</p>
            
            <div class="brief-list">
        """

        brief_groups = defaultdict(list)
        for paper in brief:
            brief_groups[paper["topic"]].append(paper)

        for topic, papers in sorted(brief_groups.items()):
            html += f"<div class='brief-topic'><h4 class='brief-topic-title'>{topic}</h4>"

            for paper in papers:
                html += f"""
                <div class="brief-item">
                    <a href="{paper['url']}" class="brief-link">{paper['title']}</a>
                </div>
                """

            html += "</div>"

        html += """
            </div>
        </div>
        """

    return html
