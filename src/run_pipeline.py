from digest_core.cache import JsonSourceCache
from digest_core.config import MAX_BRIEF_PAPERS, MAX_FEATURED_PAPERS, PROCESS_ALL_WHEN_NO_NEW
from digest_core.logging import RunLogger
from digest_core.models import PipelinePaths, PipelineSettings
from evidence.download_pdfs import download_pdf
from evidence.pdf_extract import extract_pdf_text
from evidence.pdf_sections import build_paper_context, extract_sections
from evidence.pipeline import (
    EvidenceBuilderDependencies,
    EvidencePreparationPipeline,
    FeaturedPaperEvidenceBuilder,
    build_abstract_record as _build_abstract_record,
    is_informative_abstract as _is_informative_abstract,
    make_brief_record as _make_brief_record,
    normalize_text as _normalize_text,
)
from evidence.selector import has_sufficient_summary_evidence
from evidence.sentence_ranker import rank_sentences
from pipeline.research_pipeline import ResearchDigestPipeline
from sources.arxiv import fetch_arxiv_papers
from sources.chemrxiv import fetch_chemrxiv_papers
from sources.pubmed import fetch_pubmed_papers
from sources.retrieval import LiteratureRetriever, PaperSource
from summarization.llm import summarize_papers
from summarization.narrative import generate_weekly_narrative
from web.publishing import DigestPublisher


RAW_PATH = "data/raw_papers.json"
FILTERED_PATH = "data/filtered_papers.json"
SENTENCES_PATH = "data/paper_sentences.json"
SUMMARIES_PATH = "data/summaries.json"

POSTS_DIR = "docs/posts"
INDEX_PATH = "docs/index.html"
ARCHIVE_PATH = "docs/archive.html"


def ensure_dirs():
    DigestPublisher(_default_paths()).ensure_dirs()


def save_weekly_post(html):
    return DigestPublisher(_default_paths()).save_weekly_post(html)


def save_latest_post(html):
    DigestPublisher(_default_paths()).save_latest_post(html)


def build_navigation_index(summaries, latest_post_filename):
    return DigestPublisher(_default_paths()).build_navigation_index(summaries, latest_post_filename)


def rebuild_archive():
    DigestPublisher(_default_paths()).rebuild_archive()


def build_featured_paper_record(paper):
    dependencies = EvidenceBuilderDependencies(
        download_pdf=download_pdf,
        extract_pdf_text=extract_pdf_text,
        extract_sections=extract_sections,
        build_paper_context=build_paper_context,
        rank_sentences=rank_sentences,
        evidence_validator=has_sufficient_summary_evidence,
    )
    return FeaturedPaperEvidenceBuilder(dependencies).build_featured_record(paper)


def _default_paths():
    return PipelinePaths(
        raw_papers=RAW_PATH,
        filtered_papers=FILTERED_PATH,
        clustered_papers="data/clustered_papers.json",
        paper_sentences=SENTENCES_PATH,
        summaries=SUMMARIES_PATH,
        posts_dir=POSTS_DIR,
        index=INDEX_PATH,
        archive=ARCHIVE_PATH,
    )


def _default_settings():
    return PipelineSettings(
        max_featured_papers=MAX_FEATURED_PAPERS,
        max_brief_papers=MAX_BRIEF_PAPERS,
        process_all_when_no_new=PROCESS_ALL_WHEN_NO_NEW,
    )


def build_pipeline():
    paths = _default_paths()
    settings = _default_settings()
    logger = RunLogger()

    retriever = LiteratureRetriever(
        [
            PaperSource(
                "arXiv",
                lambda: fetch_arxiv_papers(
                    days_back=settings.days_back,
                    max_results=settings.arxiv_max_results,
                ),
                cache_key="arxiv",
            ),
            PaperSource(
                "PubMed",
                lambda: fetch_pubmed_papers(
                    days_back=settings.days_back,
                    max_results=settings.pubmed_max_results,
                ),
                cache_key="pubmed",
            ),
            PaperSource(
                "ChemRxiv",
                lambda: fetch_chemrxiv_papers(days_back=settings.days_back),
                cache_key="chemrxiv",
            ),
        ],
        cache=JsonSourceCache(),
        cache_ttl_hours=settings.source_cache_ttl_hours,
        retry_attempts=settings.source_retry_attempts,
        logger=logger,
    )

    evidence_dependencies = EvidenceBuilderDependencies(
        download_pdf=download_pdf,
        extract_pdf_text=extract_pdf_text,
        extract_sections=extract_sections,
        build_paper_context=build_paper_context,
        rank_sentences=rank_sentences,
        evidence_validator=has_sufficient_summary_evidence,
    )
    evidence_pipeline = EvidencePreparationPipeline(
        FeaturedPaperEvidenceBuilder(evidence_dependencies),
        max_featured_papers=settings.max_featured_papers,
        max_brief_papers=settings.max_brief_papers,
    )

    return ResearchDigestPipeline(
        retriever=retriever,
        evidence_pipeline=evidence_pipeline,
        publisher=DigestPublisher(paths),
        paths=paths,
        settings=settings,
        summarizer=summarize_papers,
        narrative_generator=generate_weekly_narrative,
        logger=logger,
    )


def main():
    build_pipeline().run()


if __name__ == "__main__":
    main()
