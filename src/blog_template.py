def render_blog(content_html):
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI & Cheminformatics Digest — Weekly Research Briefing</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --primary: #0f766e;
            --primary-light: #14b8a6;
            --accent: #7c3aed;
            --accent-light: #a78bfa;
            --bg: #f8fafc;
            --surface: #ffffff;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --border: #e2e8f0;
            --highlight: #fef3c7;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", sans-serif;
            background: linear-gradient(135deg, var(--bg) 0%, #f1f5f9 100%);
            color: var(--text-primary);
            line-height: 1.6;
            font-size: 16px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}

        /* HEADER */
        .header {{
            text-align: center;
            margin-bottom: 60px;
            padding: 50px 20px;
        }}

        .header-logo {{
            display: inline-block;
            width: 70px;
            height: 70px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(15, 118, 110, 0.2);
        }}

        h1 {{
            font-size: 42px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 10px;
            letter-spacing: -0.5px;
        }}

        .tagline {{
            font-size: 18px;
            color: var(--text-secondary);
            font-weight: 500;
            margin-bottom: 5px;
        }}

        .publication-date {{
            font-size: 14px;
            color: var(--text-secondary);
            font-style: italic;
        }}

        /* MUST READ SECTION */
        .must-read-container {{
            margin-bottom: 70px;
        }}

        .must-read-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, var(--accent-light) 0%, var(--accent) 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 24px;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(124, 58, 237, 0.2);
        }}

        .badge-icon {{
            font-size: 16px;
        }}

        .must-read-paper {{
            background: var(--surface);
            border: 3px solid var(--accent);
            border-radius: 16px;
            padding: 50px;
            box-shadow: 0 20px 60px rgba(15, 118, 110, 0.08);
            position: relative;
            overflow: hidden;
        }}

        .must-read-paper::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 6px;
            background: linear-gradient(90deg, var(--primary) 0%, var(--accent) 100%);
        }}

        .must-read-title {{
            font-size: 32px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 20px;
            line-height: 1.3;
        }}

        .must-read-meta {{
            display: flex;
            gap: 15px;
            align-items: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}

        .topic-badge {{
            display: inline-block;
            background: var(--highlight);
            color: var(--text-primary);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}

        .rank-indicator {{
            color: var(--accent);
            font-weight: 600;
            font-size: 14px;
        }}

        .must-read-summary {{
            margin-bottom: 30px;
            color: var(--text-secondary);
            line-height: 1.8;
        }}

        .must-read-summary p {{
            margin-bottom: 16px;
        }}

        .must-read-summary strong {{
            color: var(--text-primary);
            display: block;
            margin-top: 20px;
            font-weight: 700;
        }}

        .must-read-summary ul {{
            margin-left: 24px;
            margin-top: 12px;
        }}

        .must-read-summary li {{
            margin-bottom: 10px;
        }}

        .must-read-action {{
            display: flex;
            gap: 14px;
            flex-wrap: wrap;
        }}

        .btn-primary, .btn-secondary {{
            padding: 14px 28px;
            border-radius: 8px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            border: none;
            font-size: 14px;
            transition: all 0.3s ease;
            display: inline-block;
        }}

        .btn-primary {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(15, 118, 110, 0.3);
        }}

        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(15, 118, 110, 0.4);
        }}

        .btn-secondary {{
            background: var(--border);
            color: var(--text-primary);
        }}

        .btn-secondary:hover {{
            background: var(--primary);
            color: white;
        }}

        /* SECTION HEADLINES */
        .section-headline {{
            font-size: 28px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 12px;
            margin-top: 60px;
        }}

        .section-subtitle {{
            font-size: 15px;
            color: var(--text-secondary);
            margin-bottom: 30px;
            font-weight: 500;
        }}

        /* INSIGHTS SECTION */
        .insights-container {{
            background: linear-gradient(135deg, rgba(20, 184, 166, 0.05) 0%, rgba(124, 58, 237, 0.05) 100%);
            border-left: 5px solid var(--primary);
            border-radius: 12px;
            padding: 40px;
            margin: 40px 0;
        }}

        .insights-body {{
            color: var(--text-secondary);
            font-size: 16px;
            line-height: 1.8;
        }}

        .insights-body p {{
            margin-bottom: 18px;
        }}

        /* FEATURED SECTION */
        .featured-section {{
            margin-bottom: 60px;
        }}

        .topic-group {{
            margin-bottom: 50px;
        }}

        .topic-header {{
            font-size: 20px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--primary);
        }}

        .papers-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
        }}

        .paper-card-featured {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            position: relative;
        }}

        .paper-card-featured:hover {{
            border-color: var(--primary);
            box-shadow: 0 8px 24px rgba(15, 118, 110, 0.15);
            transform: translateY(-4px);
        }}

        .paper-rank {{
            position: absolute;
            top: 16px;
            right: 16px;
            background: var(--highlight);
            color: var(--text-primary);
            font-weight: 700;
            font-size: 12px;
            padding: 6px 12px;
            border-radius: 6px;
        }}

        .paper-title-featured {{
            font-size: 17px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 16px;
            line-height: 1.4;
            margin-top: 0;
        }}

        .paper-summary-featured {{
            flex-grow: 1;
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 16px;
            line-height: 1.6;
        }}

        .paper-summary-featured p {{
            margin-bottom: 12px;
        }}

        .paper-footer {{
            border-top: 1px solid var(--border);
            padding-top: 16px;
        }}

        .link-read-more {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s ease;
        }}

        .link-read-more:hover {{
            color: var(--primary-light);
            text-decoration: underline;
        }}

        /* OPTIONAL BRIEF SECTION */
        .optional-section {{
            background: var(--bg);
            border-radius: 12px;
            padding: 40px;
            margin-top: 60px;
        }}

        .brief-list {{
            display: grid;
            gap: 30px;
        }}

        .brief-topic {{
            margin-bottom: 0;
        }}

        .brief-topic-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 16px;
        }}

        .brief-item {{
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
            transition: padding 0.2s ease;
        }}

        .brief-item:last-child {{
            border-bottom: none;
        }}

        .brief-item:hover {{
            padding-left: 8px;
        }}

        .brief-link {{
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 15px;
            font-weight: 500;
            transition: all 0.3s ease;
        }}

        .brief-link:hover {{
            color: var(--primary);
            font-weight: 600;
        }}

        /* FOOTER */
        .footer {{
            text-align: center;
            margin-top: 80px;
            padding-top: 40px;
            border-top: 2px solid var(--border);
            font-size: 14px;
            color: var(--text-secondary);
        }}

        .footer p {{
            margin-bottom: 8px;
        }}

        .footer b {{
            color: var(--primary);
            font-weight: 700;
        }}

        /* RESPONSIVE */
        @media (max-width: 768px) {{
            .container {{
                padding: 16px;
            }}

            h1 {{
                font-size: 32px;
            }}

            .must-read-paper {{
                padding: 30px;
            }}

            .must-read-title {{
                font-size: 24px;
            }}

            .papers-grid {{
                grid-template-columns: 1fr;
            }}

            .must-read-action {{
                flex-direction: column;
            }}

            .btn-primary, .btn-secondary {{
                width: 100%;
                text-align: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-logo">🧪</div>
            <h1>AI & Cheminformatics Digest</h1>
            <div class="tagline">Weekly Research Briefing for Drug Discovery Experts</div>
            <div class="publication-date">March 29, 2026</div>
        </div>

        {content_html}

        <div class="footer">
            <p>Curated from <strong>arXiv</strong>, <strong>PubMed</strong>, and <strong>ChemRxiv</strong></p>
            <p>Powered by AI-driven topic extraction and two-stage LLM summarization | <strong>abbadonaz</strong></p>
        </div>
    </div>
</body>
</html>
"""
