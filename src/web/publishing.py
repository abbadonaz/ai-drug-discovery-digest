import os
from datetime import date
from html import escape

from web.blog_template import render_blog
from web.digest import generate_digest_html, slugify_title


class DigestPublisher:
    def __init__(self, paths):
        self.paths = paths

    def ensure_dirs(self):
        os.makedirs("data", exist_ok=True)
        os.makedirs(self.paths.posts_dir, exist_ok=True)

    def save_weekly_post(self, html):
        today = date.today().isoformat()
        filename = f"{self.paths.posts_dir}/{today}.html"

        with open(filename, "w", encoding="utf-8") as file:
            file.write(html)

        return filename

    def save_latest_post(self, html):
        with open(self.paths.index, "w", encoding="utf-8") as file:
            file.write(html)

    def build_navigation_index(self, summaries, latest_post_filename):
        featured = [paper for paper in summaries if not paper.get("brief", False)]
        brief = [paper for paper in summaries if paper.get("brief", False)]
        latest_post_name = os.path.basename(latest_post_filename)

        featured_links = ""
        for idx, paper in enumerate(featured[:12], start=1):
            anchor = slugify_title(paper["title"])
            cluster = paper.get("cluster_label") or paper.get("topic", "Other")
            featured_links += f"""
            <div class="paper-card">
                <div class="paper-title">#{idx} {escape(paper["title"])}</div>
                <div class="section-subtitle">{escape(cluster)}</div>
                <a href="posts/{latest_post_name}#{anchor}">Open summary</a>
            </div>
            """

        brief_links = ""
        for paper in brief[:20]:
            brief_links += f"""
            <div class="paper-card">
                <div class="paper-title">{escape(paper["title"])}</div>
                <div class="section-subtitle">{escape(paper.get("cluster_label") or paper.get("topic", "Other"))}</div>
                <a href="{escape(paper["url"])}">Open source paper</a>
            </div>
            """

        return render_blog(
            f"""
            <div class="digest-stats">
                <div class="stat-card">
                    <span class="stat-value">{len(featured)}</span>
                    <span class="stat-label">Featured summaries</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">{len(brief)}</span>
                    <span class="stat-label">Additional references</span>
                </div>
            </div>

            <section class="must-read-container">
                <div class="must-read-badge">Navigation Hub</div>
                <article class="must-read-paper">
                    <h2 class="must-read-title">Choose where to start</h2>
                    <p class="section-subtitle">Use this homepage as the mother index for the current weekly batch. Open the full digest, jump to a featured paper summary, or browse the archive.</p>
                    <div class="must-read-action">
                        <a href="posts/{latest_post_name}" class="btn-primary">Open latest digest</a>
                        <a href="archive.html" class="btn-secondary">Browse archive</a>
                    </div>
                </article>
            </section>

            <section class="featured-section">
                <h2 class="section-headline">Featured summaries</h2>
                <p class="section-subtitle">Direct links into the latest digest for the current featured papers.</p>
                <div class="papers-grid">
                    {featured_links or '<p>No featured summaries are available for this run.</p>'}
                </div>
            </section>

            <section class="optional-section">
                <h2 class="section-headline">Additional references</h2>
                <p class="section-subtitle">Relevant papers kept as lightweight references in the current run.</p>
                <div class="papers-grid">
                    {brief_links or '<p>No additional references were included in this run.</p>'}
                </div>
            </section>
            """,
            publication_date=date.today(),
            page_title="AI Drug Discovery Digest",
            page_tagline="A navigation hub for the latest weekly summaries, paper links, and archive pages.",
        )

    def rebuild_archive(self):
        posts = sorted(os.listdir(self.paths.posts_dir), reverse=True)
        links = ""

        for post_name in posts:
            if not post_name.endswith(".html"):
                continue

            date_str = post_name.replace(".html", "")
            links += f"""
            <div class="paper-card">
                <div class="paper-title">
                    Weekly Digest - {date_str}
                </div>

                <a href="posts/{post_name}">Read digest -&gt;</a>
            </div>
            """

        page = render_blog(
            f"""
            <div class="section-title">
            Digest Archive
            </div>

            {links}
            """,
            page_title="AI Drug Discovery Digest Archive",
            page_tagline="An index of weekly digests focused on drug discovery, computational chemistry, and molecular machine learning.",
        )

        with open(self.paths.archive, "w", encoding="utf-8") as file:
            file.write(page)

    def publish(self, summaries, narrative):
        content_html = generate_digest_html(summaries, narrative)
        page = render_blog(content_html, publication_date=date.today())
        filename = self.save_weekly_post(page)
        self.save_latest_post(self.build_navigation_index(summaries, filename))
        self.rebuild_archive()
        return filename
