from html.parser import HTMLParser

import pytest

from web.digest import render_markdown


class ParsedHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


@pytest.mark.parametrize("url", [
    "http://example.org/paper", "https://example.org/paper?q=one&view=full",
    "HTTPS://example.org/paper", "mailto:scientist@example.org",
    "mailto:first@example.org,second@example.org?subject=Paper%20review",
    "papers/study.html", "../archive.html", "/posts/2026-11-07.html",
    "./paper.pdf", "#evidence", "?page=2", "papers/my%20study.pdf",
    "papers/study:2026.html", "#https:reference",
])
def test_safe_links_preserved(url):
    parsed = ParsedHTML(render_markdown(f"[Read paper]({url})"))
    links = [attrs for tag, attrs in parsed.elements if tag == "a"]
    assert len(links) == 1
    assert links[0]["href"] == url


UNSAFE_URLS = [
    "javascript:alert%281%29", "JaVaScRiPt:alert%281%29",
    "data:text/html,evil", "vbscript:evil", "file:///etc/passwd",
    "ftp://example.org/file", "//evil.example/path", "%2f%2fevil.example/path",
    "javascript&#58;evil", "jav&#x61;script:evil", "javascript&colon;evil",
    "javascript&amp;colon;evil", "%6aavascript:evil", "javascript%3Aevil",
    "%256aavascript%253Aevil", "java%09script:evil", "java%0ascript:evil",
    "java&#x0d;script:evil", "%00javascript:evil", "java\tscript:evil",
    "java\nscript:evil", "java\rscript:evil", "java\x00script:evil",
    "java\u200bscript:evil", "%20javascript:evil", "java%20script:evil",
    "https://example.org%0aevil", "https:%2f%5cevil.example",
    "https:example.org", "http:///example.org", "https://example.org:bad",
    "mailto:", "mailto:not-an-address", "mailto:user@example.org%0d%0aBcc:evil@example.org",
    "%ffjavascript:evil", "%252525252525252525256aavascript:evil",
]


@pytest.mark.parametrize("url", UNSAFE_URLS)
@pytest.mark.parametrize("image", [False, True], ids=["link", "image"])
def test_unsafe_destinations_removed(url, image):
    marker = "!" if image else ""
    parsed = ParsedHTML(render_markdown(f"{marker}[Evidence]({url})"))
    assert all("href" not in attrs and "src" not in attrs for _, attrs in parsed.elements)


@pytest.mark.parametrize("url", ["https://example.org/plot.png", "/images/plot.png", "../plot.png"])
def test_safe_images_preserved(url):
    parsed = ParsedHTML(render_markdown(f"![Assay plot]({url})"))
    images = [attrs for tag, attrs in parsed.elements if tag == "img"]
    assert images == [{"alt": "Assay plot", "src": url}]


def test_mailto_is_not_an_image_source():
    parsed = ParsedHTML(render_markdown("![Plot](mailto:user@example.org)"))
    assert all("src" not in attrs for _, attrs in parsed.elements)


@pytest.mark.parametrize("source", [
    "[Evidence][ref]\n\n[ref]: javascript:evil",
    "![Evidence][ref]\n\n[ref]: data:image/png,evil",
    "[Evidence](https://example.org){href=javascript:evil}",
    "![Evidence](https://example.org/image.png){src=data:image/png,evil}",
    "[Evidence](https://example.org){href=//evil.example/path}",
])
def test_final_tree_destinations_are_checked(source):
    parsed = ParsedHTML(render_markdown(source))
    assert all("href" not in attrs and "src" not in attrs for _, attrs in parsed.elements)


@pytest.mark.parametrize("attributes", [
    "HREF=javascript:evil", "SRC=data:image/png,evil",
    "srcset=//evil.example/plot.png", "SRCSET=data:image/png,evil",
    "ping=//evil.example/track", "onerror=evil", "OnClick=evil",
    "style=background:url(//evil.example/plot.png)",
])
def test_attribute_lists_cannot_bypass_url_boundary(attributes):
    parsed = ParsedHTML(render_markdown(f"![Plot](https://example.org/plot.png){{{attributes}}}"))
    for _, attrs in parsed.elements:
        assert not (set(attrs) & {"href", "srcset", "ping", "style", "onerror", "onclick"})
        if "src" in attrs:
            assert attrs["src"] == "https://example.org/plot.png"


def test_safe_attribute_list_formatting_preserved():
    parsed = ParsedHTML(render_markdown("![Plot](plot.png){#plot .figure width=200 height=100}"))
    image = next(attrs for tag, attrs in parsed.elements if tag == "img")
    assert image == {"src": "plot.png", "alt": "Plot", "id": "plot", "class": "figure",
                     "width": "200", "height": "100"}


@pytest.mark.parametrize("source", [
    '<script>alert(1)</script>', '<a href="javascript:evil">click</a>',
    '<img src="x" onerror="evil">',
])
def test_raw_html_remains_escaped(source):
    rendered = render_markdown(source)
    assert "&lt;" in rendered
    assert not any(tag in {"script", "a", "img"} for tag, _ in ParsedHTML(rendered).elements)


def test_ordinary_markdown_formatting_survives():
    rendered = render_markdown(
        "## Findings\n\n**Strong** and *careful* with `code` & context.\n\n"
        "- First\n- Second\n\n[Paper](https://example.org)"
    )
    for expected in ("<h2>Findings</h2>", "<strong>Strong</strong>", "<em>careful</em>",
                     "<code>code</code>", "<ul>", "<li>First</li>", "&amp; context"):
        assert expected in rendered


def test_rejected_link_preserves_label_and_image_alt():
    rendered = render_markdown("[Read evidence](javascript:evil) ![Assay plot](data:image/png,evil)")
    assert "Read evidence" in rendered
    assert 'alt="Assay plot"' in rendered
