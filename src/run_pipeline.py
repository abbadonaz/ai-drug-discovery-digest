from fetch_arxiv import fetch_arxiv_papers
from fetch_pubmed import fetch_pubmed_papers
from fetch_chemrxiv import fetch_chemrxiv_papers

from filter_papers import filter_relevant_papers

from download_pdfs import download_pdf
from pdf_extract import extract_pdf_text, split_sentences
from pdf_sections import extract_sections, build_paper_context
from sentence_ranker import rank_sentences
from paper_scoring import rank_papers
from llm_summarizer import summarize_papers

from generate_digest import generate_digest_html
from generate_narrative import generate_weekly_narrative
from blog_template import render_blog
from clean_sentences import clean_sentences
from utils import save_json


RAW_PATH = "data/raw_papers.json"
FILTERED_PATH = "data/filtered_papers.json"
SENTENCES_PATH = "data/paper_sentences.json"
SUMMARIES_PATH = "data/summaries.json"

BLOG_PATH = "docs/index.html"


def main():

    print("\n--- AI & Cheminformatics Literature Pipeline ---\n")

    # --------------------------------------------------
    # 1. Fetch papers
    # --------------------------------------------------

    print("Fetching papers from arXiv...")
    arxiv_papers = fetch_arxiv_papers(days_back=14, max_results=500)

    print("Fetching papers from PubMed...")
    pubmed_papers = fetch_pubmed_papers(days_back=14, max_results=200)

    print("Fetching papers from ChemRxiv...")
    chemrxiv_papers = fetch_chemrxiv_papers(days_back=14)

    papers = arxiv_papers + pubmed_papers + chemrxiv_papers

    print(f"Total papers collected: {len(papers)}")

    save_json(papers, RAW_PATH)

    # --------------------------------------------------
    # 2. Relevance filtering
    # --------------------------------------------------

    print("\nFiltering relevant papers...")

    filtered = filter_relevant_papers(papers)

    print(f"{len(filtered)} papers passed filtering")

    save_json(filtered, FILTERED_PATH)

    # --------------------------------------------------
    # 3. Download and process PDFs
    # --------------------------------------------------

    print("\nDownloading PDFs and extracting key sentences...")

    paper_sentences = []

    for paper in filtered[:20]:  # limit to top 20 for speed

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

    # --------------------------------------------------
    # 4. Generate summaries
    # --------------------------------------------------

    print("\nGenerating structured summaries...")

    summaries = summarize_papers(paper_sentences)
    print("\nGenerating weekly narrative...")

    summaries=rank_papers(summaries)
    narrative = generate_weekly_narrative(summaries)    

    print(f"Generated {len(summaries)} summaries")

    save_json(summaries, SUMMARIES_PATH)

    # --------------------------------------------------
    # 5. Generate blog
    # --------------------------------------------------

    print("\nGenerating blog page...")

    content_html = generate_digest_html(summaries, narrative)

    page = render_blog(content_html)

    with open(BLOG_PATH, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"\nBlog saved to: {BLOG_PATH}")

    print("\nPipeline finished successfully 🚀")


if __name__ == "__main__":
    main()