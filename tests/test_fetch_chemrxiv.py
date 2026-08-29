from sources.chemrxiv import fetch_chemrxiv_papers


def test_fetch_chemrxiv_papers_uses_direct_feed_and_parses_entries(monkeypatch):
    feed_xml = """
    <rss version="2.0">
      <channel>
        <item>
          <title>Computational chemistry for drug discovery</title>
          <link>https://chemrxiv.org/engage/chemrxiv/article-details/abc123</link>
          <description>Virtual screening and molecular docking workflow.</description>
          <pubDate>Mon, 06 Apr 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    monkeypatch.setattr("sources.chemrxiv._fetch_feed_xml", lambda url: feed_xml)

    papers = fetch_chemrxiv_papers(days_back=30)

    assert len(papers) == 1
    assert papers[0]["source"] == "chemrxiv"
    assert "Computational chemistry" in papers[0]["title"]


def test_fetch_chemrxiv_papers_falls_back_when_primary_feed_is_blocked(monkeypatch):
    blocked_html = "<html><title>Just a moment...</title><span>Enable JavaScript and cookies to continue</span></html>"
    monkeypatch.setattr("sources.chemrxiv._fetch_feed_xml", lambda url: blocked_html)
    monkeypatch.setattr(
        "sources.chemrxiv._fetch_crossref_items",
        lambda days_back, rows=200: [
            {
                "title": ["Docking benchmark for ligand design"],
                "URL": "https://doi.org/10.26434/chemrxiv-2026-xyz",
                "published": {"date-parts": [[2026, 4, 6]]},
            }
        ],
    )

    papers = fetch_chemrxiv_papers(days_back=30)

    assert len(papers) == 1
    assert "Docking benchmark" in papers[0]["title"]
