import os
from datetime import date, datetime, timezone
from collections import Counter
import json
from pathlib import Path
import uuid

from digest_core.atomic import atomic_write_text, publication_lock, replace_files
from digest_core.publication import content_hash, validate_artifact
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

        atomic_write_text(filename, html)

        return filename

    def save_latest_post(self, html):
        atomic_write_text(self.paths.index, html)

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
        atomic_write_text(self.paths.archive, self.build_archive())

    def build_archive(self, new_post=None):
        posts = set(os.listdir(self.paths.posts_dir)) if os.path.isdir(self.paths.posts_dir) else set()
        if new_post:
            posts.add(Path(new_post).name)
        posts = sorted(posts, reverse=True)
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

        return page

    def publish(self, summaries, narrative, *, artifacts=None, metadata=None, run_id=None):
        with publication_lock(Path(self.paths.index).parent / ".publication.lock"):
            return self._publish(summaries, narrative, artifacts, metadata, run_id)

    def _publish(self, summaries, narrative, artifacts, metadata, run_id):
        if not any(not paper.get("brief") for paper in summaries):
            raise ValueError("Publication requires featured summaries")
        if any(paper.get("generation_mode") == "unavailable" for paper in summaries if not paper.get("brief")):
            raise ValueError("Cannot publish failure placeholders as summaries")
        filename = f"{self.paths.posts_dir}/{date.today().isoformat()}.html"
        content_html = generate_digest_html(summaries, narrative)
        page = render_blog(content_html, publication_date=date.today())
        navigation = self.build_navigation_index(summaries, filename)
        archive = self.build_archive(filename)
        if f"posts/{Path(filename).name}" not in navigation or f"posts/{Path(filename).name}" not in archive:
            raise ValueError("Navigation does not reference the staged post")
        outputs = {Path(path): text for path, text in (artifacts or {}).items()}
        outputs[Path(self.paths.summaries)] = json.dumps(summaries, indent=2, ensure_ascii=False)
        outputs[Path(filename)] = page
        outputs[Path(self.paths.index)] = navigation
        outputs[Path(self.paths.archive)] = archive
        manifest_path = Path(self.paths.index).parent / "publication.json"
        required_paths = [filename, self.paths.index, self.paths.archive, self.paths.summaries, manifest_path]
        if len({Path(path).resolve() for path in required_paths}) != len(required_paths):
            raise ValueError("Publication paths must be distinct")
        roles = {Path(filename): "post", Path(self.paths.index): "index",
                 Path(self.paths.archive): "archive", Path(self.paths.summaries): "summaries"}
        manifest = {
            "status": "published", "run_id": run_id or uuid.uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "generation_modes": dict(Counter(paper.get("generation_mode", "unknown") for paper in summaries)),
            "artifacts": [
                {"path": os.path.relpath(path.resolve(), manifest_path.parent.resolve()),
                 "role": roles.get(path, "state"), "sha256": content_hash(text.encode("utf-8"))}
                for path, text in outputs.items()
            ],
        }
        # The marker is replaced last. Its hashes detect incomplete/mixed state.
        outputs[manifest_path] = json.dumps(manifest, indent=2, ensure_ascii=False)
        replace_files(outputs, validate_artifact)
        return filename
