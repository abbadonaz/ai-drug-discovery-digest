import importlib


MODULES = [
    "digest_core.config",
    "digest_core.cache",
    "digest_core.logging",
    "digest_core.models",
    "digest_core.env_check",
    "digest_core.utils",
    "evidence.clean_sentences",
    "evidence.download_pdfs",
    "evidence.pdf_extract",
    "evidence.pdf_sections",
    "evidence.pipeline",
    "evidence.provenance",
    "evidence.security",
    "evidence.selector",
    "evidence.sentence_ranker",
    "pipeline.deduplication",
    "pipeline.research_pipeline",
    "evaluation.harness",
    "run_pipeline",
    "sources.arxiv",
    "sources.chemrxiv",
    "sources.pubmed",
    "sources.retrieval",
    "summarization.llm",
    "summarization.narrative",
    "summarization.ollama_client",
    "triage.embeddings",
    "triage.clustering",
    "triage.filtering",
    "triage.scoring",
    "triage.taxonomy",
    "triage.topics",
    "web.blog_template",
    "web.digest",
    "web.publishing",
]


def test_all_modules_import():
    for module_name in MODULES:
        assert importlib.import_module(module_name)
