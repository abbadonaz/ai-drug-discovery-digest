import os
from datetime import date

from blog_template import render_blog
from clean_sentences import clean_sentences
from config import MAX_BRIEF_PAPERS, MAX_FEATURED_PAPERS, PROCESS_ALL_WHEN_NO_NEW
from deduplicate_papers import mark_papers_seen, split_new_and_seen_papers
from download_pdfs import download_pdf
from fetch_arxiv import fetch_arxiv_papers
from fetch_chemrxiv import fetch_chemrxiv_papers
from fetch_pubmed import fetch_pubmed_papers
from filter_papers import filter_relevant_papers
from generate_digest import generate_digest_html
from generate_narrative import generate_weekly_narrative
from llm_summarizer import summarize_papers
from paper_scoring import rank_papers
from pdf_extract import extract_pdf_text, split_sentences
from pdf_sections import build_paper_context, extract_sections
from sentence_ranker import rank_sentences
from utils import save_json


RAW_PATH = "data/raw_papers.json"
FILTERED_PATH = "data/filtered_papers.json"
SENTENCES_PATH = "data/paper_sentences.json"
SUMMARIES_PATH = "data/summaries.json"

POSTS_DIR = "docs/posts"
INDEX_PATH = "docs/index.html"


def ensure_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs(POSTS_DIR, exist_ok=True)


def save_weekly_post(html):
    today = date.today().isoformat()
    filename = f"{POSTS_DIR}/{today}.html"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    return filename


def rebuild_index():
    posts = sorted(os.listdir(POSTS_DIR), reverse=True)
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

            <a href="posts/{post_name}">Read digest -></a>
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

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(page)


def build_featured_paper_record(paper):
    pdf_path = download_pdf(paper)
    if not pdf_path:
        abstract = (paper.get("abstract") or "").strip()
        if not abstract:
            return None

        abstract_sentences = clean_sentences(split_sentences(abstract))
        if not abstract_sentences:
            abstract_sentences = [abstract]

        return {
            "title": paper["title"],
            "url": paper["url"],
            "topic": paper.get("topic", "Other"),
            "sentences": abstract_sentences[:10],
            "context": abstract,
            "sections": {"abstract": abstract},
        }

    text = extract_pdf_text(pdf_path)
    if not text:
        abstract = (paper.get("abstract") or "").strip()
        if not abstract:
            return None

        abstract_sentences = clean_sentences(split_sentences(abstract))
        if not abstract_sentences:
            abstract_sentences = [abstract]

        return {
            "title": paper["title"],
            "url": paper["url"],
            "topic": paper.get("topic", "Other"),
            "sentences": abstract_sentences[:10],
            "context": abstract,
            "sections": {"abstract": abstract},
        }

    sections = extract_sections(text)
    combined_text = build_paper_context(sections)
    sentences = clean_sentences(split_sentences(combined_text))
    ranked = rank_sentences(sentences, top_k=25)

    return {
        "title": paper["title"],
        "url": paper["url"],
        "topic": paper.get("topic", "Other"),
        "sentences": ranked,
        "context": combined_text,
        "sections": sections,
    }


def main():
    ensure_dirs()

    print("\n--- AI & Cheminformatics Literature Pipeline ---\n")

    print("Fetching papers from arXiv...")
    try:
        arxiv_papers = fetch_arxiv_papers(days_back=7, max_results=75)
        print(f"  Got {len(arxiv_papers)} arXiv papers")
    except Exception as e:
        print(f"  arXiv fetch failed: {e}")
        arxiv_papers = []

    print("Fetching papers from PubMed...")
    try:
        pubmed_papers = fetch_pubmed_papers(days_back=7, max_results=100)
        print(f"  Got {len(pubmed_papers)} PubMed papers")
    except Exception as e:
        print(f"  PubMed fetch failed: {e}")
        pubmed_papers = []

    print("Fetching papers from ChemRxiv...")
    try:
        chemrxiv_papers = fetch_chemrxiv_papers(days_back=7)
        print(f"  Got {len(chemrxiv_papers)} ChemRxiv papers")
    except Exception as e:
        print(f"  ChemRxiv fetch failed: {e}")
        chemrxiv_papers = []

    fetched_papers = arxiv_papers + pubmed_papers + chemrxiv_papers
    print(f"\nFetched {len(fetched_papers)} total papers")

    new_papers, seen_papers = split_new_and_seen_papers(fetched_papers)
    print(f"{len(new_papers)} new papers after deduplication")

    if new_papers:
        mark_papers_seen(new_papers)

    papers_to_process = new_papers
    if not papers_to_process and PROCESS_ALL_WHEN_NO_NEW:
        papers_to_process = seen_papers
        print("No new papers found; rebuilding digest from the current fetched set.")

    save_json(papers_to_process, RAW_PATH)

    if not papers_to_process:
        print("\nNo papers available for processing. Pipeline halting.")
        return

    print("\nFiltering relevant papers...")
    filtered = filter_relevant_papers(papers_to_process)
    print(f"{len(filtered)} papers passed filtering")
    save_json(filtered, FILTERED_PATH)

    print("\nDownloading PDFs and extracting key evidence...")
    paper_sentences = []
    brief_papers = []

    for paper in filtered[:MAX_FEATURED_PAPERS]:
        featured_paper = build_featured_paper_record(paper)
        if featured_paper:
            paper_sentences.append(featured_paper)

    upper_bound = MAX_FEATURED_PAPERS + MAX_BRIEF_PAPERS
    for paper in filtered[MAX_FEATURED_PAPERS:upper_bound]:
        brief_papers.append({
            "title": paper["title"],
            "url": paper["url"],
            "topic": paper.get("topic", "Other"),
            "brief": True,
        })

    print(f"Processed PDFs for {len(paper_sentences)} featured papers")
    print(f"Added {len(brief_papers)} brief references")

    save_json(paper_sentences, SENTENCES_PATH)

    if not paper_sentences:
        print("No papers processed.")
        return

    print("\nGenerating structured summaries for featured papers...")
    try:
        summaries = summarize_papers(paper_sentences)
    except Exception as error:
        print(f"Structured summarization failed at pipeline level: {error}")
        summaries = []
        for paper in paper_sentences:
            summaries.append({
                "title": paper["title"],
                "url": paper["url"],
                "topic": paper.get("topic", "Other"),
                "tldr": (
                    "### Problem\nAutomatic summarization failed.\n\n"
                    "### Method\nThe pipeline preserved this paper entry without a model-generated summary.\n\n"
                    "### Dataset / Benchmark\nNot available.\n\n"
                    "### Key Findings\n- Review the original paper for details.\n\n"
                    "### Why It Matters\nThis item stayed in the weekly digest despite a local summarization failure."
                ),
            })
    summaries = rank_papers(summaries)

    for brief in brief_papers:
        summaries.append({
            "title": brief["title"],
            "url": brief["url"],
            "topic": brief.get("topic", "Other"),
            "tldr": "",
            "brief": True,
            "score": 0,
        })

    print(f"Generated {len(summaries)} total entries ({len(paper_sentences)} featured + {len(brief_papers)} brief)")
    save_json(summaries, SUMMARIES_PATH)

    print("\nGenerating weekly narrative...")
    narrative = generate_weekly_narrative(summaries)

    print("\nGenerating blog HTML...")
    content_html = generate_digest_html(summaries, narrative)
    page = render_blog(content_html, publication_date=date.today())
    filename = save_weekly_post(page)

    print(f"\nWeekly post saved: {filename}")

    rebuild_index()
    print("\nHomepage updated")
    print("\nPipeline finished successfully")


if __name__ == "__main__":
    main()
