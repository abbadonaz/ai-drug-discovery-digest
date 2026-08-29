from datetime import date, datetime


GITHUB_PROFILE = "https://github.com/abbadonaz"
GITHUB_AVATAR = "https://github.com/abbadonaz.png"


def _format_publication_date(value=None):
    if value is None:
        return date.today().strftime("%B %d, %Y")

    if isinstance(value, datetime):
        return value.strftime("%B %d, %Y")

    if isinstance(value, date):
        return value.strftime("%B %d, %Y")

    return str(value)


def render_blog(content_html, publication_date=None, page_title=None, page_tagline=None):
    title = page_title or "AI Drug Discovery Digest"
    tagline = page_tagline or "Weekly literature intelligence for drug discovery, cheminformatics, and molecular AI"
    publication_label = _format_publication_date(publication_date)

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            box-sizing: border-box;
        }}

        :root {{
            --bg: #eef3f5;
            --bg-accent: #dde9ec;
            --paper: rgba(255, 255, 255, 0.92);
            --paper-strong: #ffffff;
            --ink: #13212b;
            --muted: #51626f;
            --line: #cad7de;
            --teal: #0c6b63;
            --teal-soft: #dff2ee;
            --slate: #d9e3ea;
            --gold: #b8892d;
            --gold-soft: #f5edd7;
            --shadow: 0 24px 60px rgba(19, 33, 43, 0.10);
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            margin: 0;
            color: var(--ink);
            background:
                radial-gradient(circle at top left, rgba(12, 107, 99, 0.10), transparent 30%),
                radial-gradient(circle at top right, rgba(184, 137, 45, 0.10), transparent 28%),
                linear-gradient(180deg, var(--bg) 0%, #f7fafb 100%);
            font-family: Georgia, "Times New Roman", serif;
            line-height: 1.65;
        }}

        a {{
            color: var(--teal);
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        .page-shell {{
            max-width: 1180px;
            margin: 0 auto;
            padding: 28px 18px 72px;
        }}

        .hero {{
            background: linear-gradient(145deg, rgba(255,255,255,0.96), rgba(248,251,252,0.88));
            border: 1px solid rgba(202, 215, 222, 0.9);
            border-radius: 28px;
            box-shadow: var(--shadow);
            overflow: hidden;
            position: relative;
            margin-bottom: 34px;
        }}

        .hero::before {{
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(135deg, rgba(12, 107, 99, 0.12), transparent 45%),
                linear-gradient(315deg, rgba(184, 137, 45, 0.12), transparent 42%);
            pointer-events: none;
        }}

        .hero-inner {{
            position: relative;
            padding: 32px;
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 24px;
            align-items: start;
        }}

        .eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 8px 14px;
            border-radius: 999px;
            background: var(--teal-soft);
            color: var(--teal);
            font-family: "Segoe UI", sans-serif;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }}

        .hero h1 {{
            margin: 18px 0 10px;
            font-size: clamp(2.2rem, 4.6vw, 4rem);
            line-height: 1.05;
            letter-spacing: -0.03em;
        }}

        .hero p {{
            margin: 0;
            max-width: 760px;
            color: var(--muted);
            font-size: 1.05rem;
        }}

        .meta-strip {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 22px;
            font-family: "Segoe UI", sans-serif;
            color: var(--muted);
            font-size: 0.92rem;
        }}

        .meta-chip {{
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(255,255,255,0.82);
            border: 1px solid var(--line);
        }}

        .profile-card {{
            width: min(280px, 100%);
            background: rgba(255,255,255,0.84);
            border: 1px solid rgba(202, 215, 222, 0.95);
            border-radius: 22px;
            padding: 20px;
            backdrop-filter: blur(8px);
        }}

        .profile-card img {{
            width: 76px;
            height: 76px;
            border-radius: 18px;
            display: block;
            margin-bottom: 14px;
            box-shadow: 0 10px 24px rgba(19, 33, 43, 0.18);
        }}

        .profile-card strong {{
            display: block;
            font-family: "Segoe UI", sans-serif;
            font-size: 1rem;
        }}

        .profile-card span {{
            display: block;
            color: var(--muted);
            font-family: "Segoe UI", sans-serif;
            font-size: 0.92rem;
            margin: 6px 0 14px;
        }}

        .profile-card a {{
            display: inline-block;
            padding: 10px 14px;
            border-radius: 999px;
            background: var(--ink);
            color: white;
            font-family: "Segoe UI", sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
        }}

        .profile-card a:hover {{
            text-decoration: none;
            background: var(--teal);
        }}

        .content-frame {{
            background: var(--paper);
            border: 1px solid rgba(202, 215, 222, 0.92);
            border-radius: 26px;
            box-shadow: var(--shadow);
            padding: 26px;
        }}

        .digest-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 26px;
        }}

        .stat-card {{
            background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(239,245,247,0.95));
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px 18px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .stat-value {{
            font-family: "Segoe UI", sans-serif;
            font-size: 1.9rem;
            font-weight: 700;
            color: var(--ink);
        }}

        .stat-label {{
            color: var(--muted);
            font-family: "Segoe UI", sans-serif;
            font-size: 0.92rem;
        }}

        .section-headline, .section-title {{
            font-family: "Segoe UI", sans-serif;
            font-size: clamp(1.5rem, 3vw, 2.2rem);
            line-height: 1.15;
            margin: 0 0 12px;
            letter-spacing: -0.03em;
        }}

        .section-subtitle {{
            margin: 0 0 24px;
            color: var(--muted);
            font-family: "Segoe UI", sans-serif;
        }}

        .footer {{
            margin-top: 28px;
            padding: 22px 8px 0;
            border-top: 1px solid var(--line);
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            justify-content: space-between;
            color: var(--muted);
            font-family: "Segoe UI", sans-serif;
            font-size: 0.92rem;
        }}

        .paper-card {{
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 20px;
            background: var(--paper-strong);
            margin-bottom: 18px;
        }}

        .must-read-container {{
            margin-bottom: 32px;
        }}

        .must-read-badge {{
            display: inline-block;
            margin-bottom: 12px;
            padding: 8px 12px;
            border-radius: 999px;
            background: var(--gold-soft);
            color: #7b5b18;
            font-family: "Segoe UI", sans-serif;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        .must-read-paper, .insights-container, .optional-section {{
            border: 1px solid var(--line);
            border-radius: 22px;
            background: rgba(255,255,255,0.9);
            padding: 24px;
        }}

        .must-read-paper {{
            background: linear-gradient(180deg, rgba(255,255,255,0.97), rgba(248,252,251,0.92));
        }}

        .must-read-title {{
            margin: 12px 0 14px;
            font-size: clamp(1.7rem, 3vw, 2.4rem);
            line-height: 1.18;
        }}

        .must-read-meta, .must-read-action {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
        }}

        .must-read-summary, .insights-body, .paper-summary-featured {{
            color: var(--ink);
        }}

        .must-read-summary p, .insights-body p, .paper-summary-featured p {{
            margin: 0 0 12px;
        }}

        .must-read-summary ul, .insights-body ul, .paper-summary-featured ul {{
            margin: 0 0 12px 20px;
        }}

        .topic-badge, .rank-indicator {{
            display: inline-flex;
            align-items: center;
            min-height: 34px;
            padding: 6px 12px;
            border-radius: 999px;
            font-family: "Segoe UI", sans-serif;
            font-size: 0.88rem;
            border: 1px solid var(--line);
        }}

        .topic-badge {{
            background: var(--teal-soft);
            color: var(--teal);
            font-weight: 700;
        }}

        .rank-indicator {{
            background: rgba(255,255,255,0.9);
            color: var(--muted);
        }}

        .btn-primary, .btn-secondary {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 44px;
            padding: 10px 18px;
            border-radius: 999px;
            font-family: "Segoe UI", sans-serif;
            font-weight: 600;
            text-decoration: none;
        }}

        .btn-primary {{
            background: var(--ink);
            color: white;
        }}

        .btn-secondary {{
            background: white;
            color: var(--teal);
            border: 1px solid var(--line);
        }}

        .featured-section {{
            margin-top: 34px;
        }}

        .topic-group {{
            margin-top: 28px;
        }}

        .topic-header {{
            margin: 0 0 14px;
            font-family: "Segoe UI", sans-serif;
            font-size: 1.15rem;
            color: var(--teal);
        }}

        .papers-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
            gap: 18px;
        }}

        .paper-card-featured {{
            position: relative;
            background: rgba(255,255,255,0.94);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 20px;
            min-height: 100%;
        }}

        .paper-rank {{
            position: absolute;
            top: 16px;
            right: 16px;
            padding: 6px 10px;
            border-radius: 999px;
            background: var(--gold-soft);
            color: #7b5b18;
            font-family: "Segoe UI", sans-serif;
            font-size: 0.8rem;
            font-weight: 700;
        }}

        .paper-title-featured {{
            margin: 0 0 12px;
            padding-right: 56px;
            font-size: 1.15rem;
            line-height: 1.3;
        }}

        .paper-footer {{
            margin-top: 16px;
            padding-top: 14px;
            border-top: 1px solid var(--line);
            font-family: "Segoe UI", sans-serif;
        }}

        .link-read-more {{
            font-weight: 700;
        }}

        .brief-list {{
            display: grid;
            gap: 18px;
        }}

        .brief-topic-title {{
            margin: 0 0 10px;
            font-family: "Segoe UI", sans-serif;
            color: var(--teal);
        }}

        .brief-item {{
            padding: 10px 0;
            border-bottom: 1px solid var(--line);
        }}

        .brief-item:last-child {{
            border-bottom: 0;
        }}

        .brief-link {{
            font-family: "Segoe UI", sans-serif;
            font-weight: 600;
        }}

        .paper-title {{
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .briefing-panel, .comparison-section {{
            border: 1px solid var(--line);
            border-radius: 12px;
            background: rgba(255,255,255,0.94);
            padding: 24px;
            margin-bottom: 24px;
        }}

        .briefing-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 18px;
        }}

        .briefing-block {{
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #ffffff;
            padding: 16px;
        }}

        .briefing-block h3 {{
            margin: 0 0 10px;
            font-family: "Segoe UI", sans-serif;
            font-size: 1rem;
            color: var(--ink);
        }}

        .signal-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: grid;
            gap: 8px;
        }}

        .signal-list li {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            border-bottom: 1px solid var(--line);
            padding-bottom: 8px;
            font-family: "Segoe UI", sans-serif;
        }}

        .signal-list li:last-child {{
            border-bottom: 0;
            padding-bottom: 0;
        }}

        .signal-list span {{
            color: var(--muted);
            white-space: nowrap;
        }}

        .cluster-grid {{
            display: grid;
            gap: 12px;
        }}

        .cluster-row {{
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 14px;
            align-items: start;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #ffffff;
            padding: 16px;
        }}

        .cluster-row h3 {{
            margin: 0 0 6px;
            color: var(--teal);
            font-family: "Segoe UI", sans-serif;
            font-size: 1rem;
        }}

        .cluster-row p {{
            margin: 0;
            color: var(--muted);
            font-family: "Segoe UI", sans-serif;
            font-size: 0.95rem;
        }}

        .cluster-row span, .paper-meta-line span {{
            display: inline-flex;
            align-items: center;
            min-height: 28px;
            padding: 4px 8px;
            border-radius: 8px;
            background: #e8ebf6;
            color: #4d5c91;
            font-family: "Segoe UI", sans-serif;
            font-size: 0.82rem;
            font-weight: 700;
        }}

        .table-wrap {{
            overflow-x: auto;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #ffffff;
        }}

        .comparison-table {{
            width: 100%;
            min-width: 760px;
            border-collapse: collapse;
            font-family: "Segoe UI", sans-serif;
            font-size: 0.92rem;
        }}

        .comparison-table th, .comparison-table td {{
            padding: 12px 14px;
            border-bottom: 1px solid var(--line);
            vertical-align: top;
            text-align: left;
        }}

        .comparison-table th {{
            background: #f7fafb;
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }}

        .comparison-table tr:last-child td {{
            border-bottom: 0;
        }}

        .paper-meta-line {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }}

        .evidence-box {{
            margin-top: 16px;
            border-top: 1px solid var(--line);
            padding-top: 14px;
        }}

        .evidence-box h5 {{
            margin: 0 0 8px;
            color: var(--muted);
            font-family: "Segoe UI", sans-serif;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }}

        .evidence-detail {{
            border: 1px solid var(--line);
            border-radius: 8px;
            margin-top: 8px;
            background: #fbfcfc;
        }}

        .evidence-detail summary {{
            cursor: pointer;
            padding: 10px 12px;
            font-family: "Segoe UI", sans-serif;
            font-weight: 700;
            font-size: 0.9rem;
        }}

        .evidence-detail ul {{
            margin: 0;
            padding: 0 12px 12px 28px;
        }}

        .evidence-detail li {{
            margin: 8px 0;
            color: var(--muted);
            font-family: "Segoe UI", sans-serif;
            font-size: 0.9rem;
        }}

        .evidence-detail li span {{
            display: inline-block;
            margin-right: 8px;
            color: #9c4558;
            font-weight: 700;
        }}

        .hero, .content-frame, .must-read-paper, .insights-container, .optional-section, .paper-card, .paper-card-featured, .stat-card {{
            border-radius: 10px;
        }}

        .hero h1, .section-headline, .section-title {{
            letter-spacing: 0;
        }}

        .topic-tabs-section {{
            border: 1px solid var(--line);
            border-radius: 12px;
            background: rgba(255,255,255,0.94);
            padding: 24px;
            margin-top: 28px;
        }}

        .topic-tabs {{
            display: grid;
            gap: 18px;
        }}

        .topic-tab-controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            border-bottom: 1px solid var(--line);
            padding-bottom: 14px;
        }}

        .topic-tab-input {{
            position: absolute;
            opacity: 0;
            pointer-events: none;
        }}

        .topic-tab-label {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            min-height: 42px;
            padding: 8px 12px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #ffffff;
            color: var(--muted);
            cursor: pointer;
            font-family: "Segoe UI", sans-serif;
            font-size: 0.9rem;
            font-weight: 700;
        }}

        .topic-tab-label strong {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 34px;
            min-height: 24px;
            padding: 2px 7px;
            border-radius: 999px;
            background: #f1f5f7;
            color: var(--ink);
            font-size: 0.78rem;
        }}

        .topic-tab-input:checked + .topic-tab-label {{
            border-color: rgba(12, 107, 99, 0.45);
            background: var(--teal-soft);
            color: var(--teal);
        }}

        .topic-tab-input:focus-visible + .topic-tab-label {{
            outline: 3px solid rgba(12, 107, 99, 0.22);
            outline-offset: 2px;
        }}

        .topic-tab-panel {{
            display: none;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: #ffffff;
            padding: 18px;
        }}

        .topic-tab-controls:has(#topic-tab-0:checked) ~ .topic-tab-panels #topic-panel-0,
        .topic-tab-controls:has(#topic-tab-1:checked) ~ .topic-tab-panels #topic-panel-1,
        .topic-tab-controls:has(#topic-tab-2:checked) ~ .topic-tab-panels #topic-panel-2,
        .topic-tab-controls:has(#topic-tab-3:checked) ~ .topic-tab-panels #topic-panel-3,
        .topic-tab-controls:has(#topic-tab-4:checked) ~ .topic-tab-panels #topic-panel-4,
        .topic-tab-controls:has(#topic-tab-5:checked) ~ .topic-tab-panels #topic-panel-5,
        .topic-tab-controls:has(#topic-tab-6:checked) ~ .topic-tab-panels #topic-panel-6,
        .topic-tab-controls:has(#topic-tab-7:checked) ~ .topic-tab-panels #topic-panel-7,
        .topic-tab-controls:has(#topic-tab-8:checked) ~ .topic-tab-panels #topic-panel-8,
        .topic-tab-controls:has(#topic-tab-9:checked) ~ .topic-tab-panels #topic-panel-9 {{
            display: block;
        }}

        .topic-panel-header {{
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 16px;
            align-items: start;
            margin-bottom: 18px;
        }}

        .topic-panel-header h3 {{
            margin: 0 0 4px;
            font-family: "Segoe UI", sans-serif;
            font-size: 1.25rem;
        }}

        .topic-panel-header p {{
            margin: 0;
            color: var(--muted);
            font-family: "Segoe UI", sans-serif;
        }}

        .topic-panel-header > span {{
            display: inline-flex;
            align-items: center;
            min-height: 32px;
            padding: 5px 10px;
            border-radius: 8px;
            background: var(--gold-soft);
            color: #7b5b18;
            font-family: "Segoe UI", sans-serif;
            font-size: 0.82rem;
            font-weight: 800;
        }}

        .topic-panel-grid {{
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(260px, 0.38fr);
            gap: 18px;
            align-items: start;
        }}

        .topic-panel-grid h4, .topic-reference-panel h4 {{
            margin: 0 0 12px;
            font-family: "Segoe UI", sans-serif;
            color: var(--ink);
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }}

        .topic-reference-panel {{
            position: sticky;
            top: 16px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #f9fbfc;
            padding: 14px;
        }}

        .compact-reference-list {{
            gap: 0;
        }}

        @media (max-width: 900px) {{
            .hero-inner {{
                grid-template-columns: 1fr;
            }}

            .profile-card {{
                width: 100%;
            }}
        }}

        @media (max-width: 680px) {{
            .page-shell {{
                padding: 16px 12px 48px;
            }}

            .hero-inner, .content-frame {{
                padding: 18px;
            }}

            .footer {{
                flex-direction: column;
            }}

            .cluster-row {{
                grid-template-columns: 1fr;
            }}

            .signal-list li {{
                flex-direction: column;
                gap: 2px;
            }}

            .topic-panel-header, .topic-panel-grid {{
                grid-template-columns: 1fr;
            }}

            .topic-reference-panel {{
                position: static;
            }}
        }}
    </style>
</head>
<body>
    <div class="page-shell">
        <header class="hero">
            <div class="hero-inner">
                <div>
                    <div class="eyebrow">Scientific Literature Intelligence</div>
                    <h1>{title}</h1>
                    <p>{tagline}</p>
                    <div class="meta-strip">
                        <div class="meta-chip">Published {publication_label}</div>
                        <div class="meta-chip">Sources: arXiv, PubMed, ChemRxiv</div>
                        <div class="meta-chip">Local summarization with Ollama</div>
                    </div>
                </div>
                <aside class="profile-card">
                    <img src="{GITHUB_AVATAR}" alt="GitHub avatar for abbadonaz">
                    <strong>abbadonaz</strong>
                    <span>Maintainer of this automated digest for drug discovery and molecular AI.</span>
                    <a href="{GITHUB_PROFILE}">View GitHub Profile</a>
                </aside>
            </div>
        </header>

        <main class="content-frame">
            {content_html}
            <footer class="footer">
                <div>Curated pipeline for recent literature triage, evidence extraction, and scientific summarization.</div>
                <div>Built for GitHub Pages and local LLM workflows.</div>
            </footer>
        </main>
    </div>
</body>
</html>
"""
