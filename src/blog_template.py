def render_blog(content_html):

    return f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>AI & Cheminformatics Weekly</title>

<style>

body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f8fafc;
    color: #0f172a;
    max-width: 960px;
    margin: auto;
    padding: 40px;
}}

.header {{
    text-align: center;
    margin-bottom: 60px;
}}

.logo {{
    width: 90px;
    border-radius: 50%;
    margin-bottom: 10px;
}}

h1 {{
    font-size: 40px;
    margin-bottom: 8px;
}}

.tagline {{
    font-size: 18px;
    color: #64748b;
}}

.hero {{
    background: white;
    padding: 30px;
    border-radius: 14px;
    margin-bottom: 40px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.06);
}}

.trend {{
    background: #eef2ff;
    padding: 25px;
    border-radius: 12px;
    margin-bottom: 40px;
}}

.section-title {{
    margin-top: 60px;
    margin-bottom: 20px;
    font-size: 24px;
    font-weight: 600;
}}

.paper-card {{
    background: white;
    padding: 26px;
    border-radius: 12px;
    margin-bottom: 22px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}}

.paper-title {{
    font-weight: 600;
    font-size: 19px;
    margin-bottom: 6px;
}}

.meta {{
    font-size: 13px;
    color: #64748b;
    margin-bottom: 12px;
}}

.summary p {{
    margin-bottom: 10px;
    line-height: 1.6;
}}

.summary strong {{
    display: block;
    margin-top: 10px;
    font-weight: 600;
}}

.summary ul {{
    margin-left: 18px;
    margin-bottom: 12px;
}}

.summary li {{
    margin-bottom: 6px;
}}

a {{
    color: #2563eb;
    text-decoration: none;
    font-weight: 500;
}}

a:hover {{
    text-decoration: underline;
}}

.footer {{
    text-align: center;
    margin-top: 80px;
    font-size: 14px;
    color: #64748b;
}}

</style>

</head>

<body>

<div class="header">

<img class="logo" src="https://github.com/abbadonaz.png">

<h1>Weekly Science Digest</h1>

<div class="tagline">
☕ Sunday Coffee Briefing on Drug Discovery & Molecular AI
</div>

</div>

{content_html}

<div class="footer">

Generated automatically from arXiv, PubMed & ChemRxiv.<br>
Curated by <b>abbadonaz</b>

</div>

</body>

</html>
"""