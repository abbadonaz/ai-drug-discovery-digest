from pathlib import Path
from types import SimpleNamespace

from web.blog_template import render_blog
from evidence.download_pdfs import _is_safe_pdf_content, _looks_like_pdf_response, get_pdf_filename
from sources.chemrxiv import fetch_chemrxiv_papers, keyword_match
from sources.pubmed import fetch_pubmed_papers
from web.digest import generate_digest_html, render_markdown
from summarization.narrative import build_trend_input
from evidence.pdf_sections import build_paper_context, extract_sections
from triage.topics import classify_topic


def test_keyword_match_identifies_domain_language():
    assert keyword_match("A study of virtual screening and ADMET modeling")


def test_keyword_match_requires_molecular_context_for_generic_ml_terms():
    assert keyword_match("Conformal prediction for molecular property prediction in drug discovery")
    assert not keyword_match("Conformal prediction for medical image segmentation")


def test_fetch_chemrxiv_papers_handles_html_and_missing_entries(monkeypatch):
    monkeypatch.setattr(
        "sources.chemrxiv._fetch_feed_xml",
        lambda url: "<rss />",
    )
    feed = SimpleNamespace(
        entries=[
            SimpleNamespace(
                published_parsed=(2026, 4, 5, 0, 0, 0, 0, 0, 0),
                title="<b>Docking benchmark</b>",
                summary="<p>Virtual screening for drug discovery</p>",
                link="https://chemrxiv.org/example",
            ),
            SimpleNamespace(
                published_parsed=None,
                title="Ignored",
                summary="Ignored",
                link="https://chemrxiv.org/ignored",
            ),
        ]
    )
    monkeypatch.setattr("sources.chemrxiv.feedparser.parse", lambda _: feed)

    papers = fetch_chemrxiv_papers(days_back=30)

    assert len(papers) == 1
    assert papers[0]["title"] == "Docking benchmark"


def test_fetch_pubmed_papers_parses_labeled_abstract(monkeypatch):
    monkeypatch.setattr(
        "sources.pubmed.Entrez.esearch",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        "sources.pubmed.Entrez.read",
        lambda handle: {"IdList": ["12345"]},
    )
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>12345</PMID>
          <Article>
            <ArticleTitle>Docking for lead discovery</ArticleTitle>
            <Abstract>
              <AbstractText Label="Background">Protein-ligand docking remains central.</AbstractText>
              <AbstractText Label="Results">The model improves enrichment.</AbstractText>
            </Abstract>
            <Journal>
              <JournalIssue>
                <PubDate>
                  <Year>2026</Year>
                  <Month>4</Month>
                  <Day>5</Day>
                </PubDate>
              </JournalIssue>
            </Journal>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    monkeypatch.setattr(
        "sources.pubmed.Entrez.efetch",
        lambda **kwargs: SimpleNamespace(read=lambda: xml),
    )

    papers = fetch_pubmed_papers(days_back=30, max_results=5)

    assert len(papers) == 1
    assert "Background:" in papers[0]["abstract"]
    assert papers[0]["url"].endswith("/12345/")


def test_extract_sections_uses_section_boundaries():
    text = (
        "Abstract This is the abstract. "
        "Introduction This introduces the problem. "
        "Results This reports the main experiment. "
        "Conclusion This closes the paper."
    )

    sections = extract_sections(text)
    context = build_paper_context(sections)

    assert "Introduction" in sections["introduction"]
    assert "Conclusion" in context


def test_extract_sections_trim_long_sections_at_sentence_boundary():
    text = (
        "Abstract "
        + ("This is a complete scientific sentence with enough detail to stay in the extracted section. " * 120)
        + "Introduction This introduces the problem. "
        + "Conclusion This closes the paper."
    )

    sections = extract_sections(text)

    assert sections["abstract"].endswith(".")


def test_generate_digest_html_and_blog_template_render_scientific_layout():
    summaries = [
        {
            "title": "Paper A",
            "url": "https://example.org/a",
            "topic": "Docking & Structure-Based Design",
            "cluster_label": "Structure-Based Design",
            "cluster_overview": "Structure-based design is represented by one paper.",
            "tldr": "### Problem\nProtein-ligand docking is hard.\n### Key Findings\n- Better enrichment.",
            "score": 12,
            "selection_score": 0.87,
            "provenance": [
                {
                    "claim": "Protein-ligand docking is hard.",
                    "evidence": [
                        {
                            "section": "abstract",
                            "text": "Protein-ligand docking remains difficult in benchmark settings.",
                        }
                    ],
                }
            ],
        },
        {
            "title": "Paper B",
            "url": "https://example.org/b",
            "topic": "Computational Chemistry",
            "tldr": "### Problem\nFree-energy estimation is expensive.",
        },
        {
            "title": "Paper C",
            "url": "https://example.org/c",
            "topic": "Other",
            "tldr": "",
            "brief": True,
        },
    ]

    digest = generate_digest_html(summaries, "A strong week for structure-aware modeling.")
    page = render_blog(digest, publication_date="April 06, 2026")

    assert "Editor's pick" not in digest
    assert "Weekly research themes" in digest
    assert "Weekly literature map" in digest
    assert "Structure-Based Design" in digest
    assert "At-a-glance comparison" in digest
    assert "<th>Selection</th>" not in digest
    assert "Evidence trace" in digest
    assert "Explore by research category" in digest
    assert "topic-tab-label" in digest
    assert "GitHub avatar for abbadonaz" in page
    assert "Published April 06, 2026" in page


def test_render_markdown_handles_empty_text():
    assert "No summary available" in render_markdown("")


def test_render_markdown_escapes_html():
    rendered = render_markdown("<script>alert(1)</script>")

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_build_trend_input_filters_empty_summaries():
    context = build_trend_input([
        {"topic": "Docking", "tldr": "Concise summary"},
        {"topic": "Other", "tldr": ""},
    ])

    assert "Topic: Docking" in context
    assert "Topic: Other" not in context


def test_classify_topic_captures_generative_chemistry():
    topic = classify_topic({
        "title": "Diffusion models for de novo molecular design",
        "abstract": "A generative chemistry workflow for molecule optimization and compound design.",
    })

    assert topic == "Generative Chemistry & Molecular Design"


def test_classify_topic_captures_structure_based_modeling():
    topic = classify_topic({
        "title": "Docking benchmark for protein-ligand pose prediction",
        "abstract": "A structure-based drug design study evaluates scoring functions for virtual screening.",
    })

    assert topic == "Structure-Based Modeling & Docking"


def test_get_pdf_filename_sanitizes_urls():
    path = get_pdf_filename({"pdf_url": "https://example.org/files/paper:name.pdf"})
    assert path == Path("data/pdfs/paper_name.pdf")


def test_pdf_download_validators_reject_non_pdf_content():
    assert _looks_like_pdf_response("https://example.org/paper.pdf", "application/octet-stream")
    assert not _looks_like_pdf_response("https://example.org/paper", "text/html")
    assert _is_safe_pdf_content(b"%PDF-1.7\nbody")
    assert not _is_safe_pdf_content(b"<html>not a pdf</html>")
