import os
from datetime import date

from fetch_arxiv import fetch_arxiv_papers
from fetch_pubmed import fetch_pubmed_papers
from fetch_chemrxiv import fetch_chemrxiv_papers

from filter_papers import filter_relevant_papers
from deduplicate_papers import filter_new_papers

from download_pdfs import download_pdf
from pdf_extract import extract_pdf_text, split_sentences
from pdf_sections import extract_sections, build_paper_context

from sentence_ranker import rank_sentences
from clean_sentences import clean_sentences

from llm_summarizer import summarize_papers
from paper_scoring import rank_papers
from generate_narrative import generate_weekly_narrative

from generate_digest import generate_digest_html
from blog_template import render_blog

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

    for p in posts:

        if not p.endswith(".html"):
            continue

        date_str = p.replace(".html", "")

        links += f"""
        <div class="paper-card">
            <div class="paper-title">
                Weekly Digest — {date_str}
            </div>

            <a href="posts/{p}">Read digest →</a>
        </div>
        """

    page = render_blog(
        f"""
        <div class="section-title">
        AI Drug Discovery Weekly
        </div>

        {links}
        """
    )

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(page)


def main():

    ensure_dirs()

    print("\n--- AI & Cheminformatics Literature Pipeline ---\n")

    # --------------------------------------------------
    # 1 Fetch papers
    # --------------------------------------------------

    print("Fetching papers from arXiv...")
    arxiv_papers = fetch_arxiv_papers(days_back=14, max_results=500)

    print("Fetching papers from PubMed...")
    pubmed_papers = fetch_pubmed_papers(days_back=14, max_results=200)

    print("Fetching papers from ChemRxiv...")
    chemrxiv_papers = fetch_chemrxiv_papers(days_back=14)

    papers = arxiv_papers + pubmed_papers + chemrxiv_papers

    print(f"Fetched {len(papers)} papers")

    # remove duplicates across runs
    papers = filter_new_papers(papers)

    print(f"{len(papers)} new papers after deduplication")

    save_json(papers, RAW_PATH)

    if not papers:
        print("No new papers found.")
        return

    # --------------------------------------------------
    # 2 Relevance filtering
    # --------------------------------------------------

    print("\nFiltering relevant papers...")

    filtered = filter_relevant_papers(papers)

    print(f"{len(filtered)} papers passed filtering")

    save_json(filtered, FILTERED_PATH)

    # --------------------------------------------------
    # 3 Download and process PDFs
    # --------------------------------------------------

    print("\nDownloading PDFs and extracting key sentences...")

    paper_sentences = []

    for paper in filtered[:20]:  # keep runtime manageable

        pdf_path = download_pdf(paper)

        if not pdf_path:
            continue

        text = extract_pdf_text(pdf_path)

        if not text:
            continue

        sections = extract_sections(text)

        combined_text = build_paper_context(sections)

        sentences = split_sentences(combined_text)

        sentences = clean_sentences(sentences)

        ranked = rank_sentences(sentences, top_k=25)

        paper_sentences.append({
            "title": paper["title"],
            "url": paper["url"],
            "topic": paper.get("topic", "Other"),
            "sentences": ranked
        })

    print(f"Processed PDFs for {len(paper_sentences)} papers")

    save_json(paper_sentences, SENTENCES_PATH)

    if not paper_sentences:
        print("No papers processed.")
        return

    # --------------------------------------------------
    # 4 Generate summaries
    # --------------------------------------------------

    print("\nGenerating structured summaries...")

    summaries = summarize_papers(paper_sentences)

    summaries = rank_papers(summaries)

    print(f"Generated {len(summaries)} summaries")

    save_json(summaries, SUMMARIES_PATH)

    # --------------------------------------------------
    # 5 Weekly narrative
    # --------------------------------------------------

    print("\nGenerating weekly narrative...")

    narrative = generate_weekly_narrative(summaries)

    # --------------------------------------------------
    # 6 Generate blog page
    # --------------------------------------------------

    print("\nGenerating blog HTML...")

    content_html = generate_digest_html(summaries, narrative)

    page = render_blog(content_html)

    filename = save_weekly_post(page)

    print(f"\nWeekly post saved: {filename}")

    # rebuild homepage

    rebuild_index()

    print("\nHomepage updated")

    print("\nPipeline finished successfully 🚀")


if __name__ == "__main__":
    main()