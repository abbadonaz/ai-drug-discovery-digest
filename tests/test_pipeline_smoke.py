import importlib


MODULES = [
    "blog_template",
    "clean_sentences",
    "config",
    "deduplicate_papers",
    "download_pdfs",
    "embeddings",
    "evidence_selector",
    "fetch_arxiv",
    "fetch_chemrxiv",
    "fetch_pubmed",
    "filter_papers",
    "generate_digest",
    "generate_narrative",
    "llm_summarizer",
    "paper_scoring",
    "pdf_extract",
    "pdf_sections",
    "run_pipeline",
    "research_taxonomy",
    "security",
    "sentence_ranker",
    "topics",
    "utils",
]


def test_all_modules_import():
    for module_name in MODULES:
        assert importlib.import_module(module_name)
