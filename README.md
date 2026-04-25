# AI Drug Discovery Digest

`AI Drug Discovery Digest` is an automated literature triage and publishing pipeline for drug discovery, cheminformatics, computational chemistry, and molecular machine learning.

It collects recent papers from `arXiv`, `PubMed`, and `ChemRxiv`, filters them for field relevance, extracts the most informative evidence from PDFs or abstracts, summarizes them locally with `Ollama`, and publishes a polished HTML digest suitable for `GitHub Pages`.

The project is designed for people who want a scientist-friendly weekly briefing without manually scanning dozens of papers.

## Highlights

| Capability | What it does |
| --- | --- |
| Weekly literature retrieval | Collects recent papers from arXiv, PubMed, and ChemRxiv |
| Field-focused triage | Prioritizes domain relevance instead of trying to judge scientific merit |
| Evidence-first summarization | Extracts and ranks relevant paper snippets before local LLM summarization |
| Safe local inference | Uses Ollama locally and adds prompt-injection filtering for fetched text |
| Robust fallback behavior | Survives missing PDFs, broken JSON cache files, blocked ChemRxiv RSS, and Ollama runner failures |
| Publishing-ready output | Generates a professional HTML digest suitable for GitHub Pages |

## Who This Is For

- research scientists who want a faster way to screen weekly literature
- cheminformatics or molecular AI practitioners who want a reproducible triage pipeline
- developers building local-first scientific intelligence workflows
- anyone who wants an automated research digest published from code

## Why This Project Exists

Modern molecular AI literature moves too quickly for manual review alone. This repository helps solve that by automating the most repetitive parts of literature surveillance:

- finding new papers across preprint and biomedical sources
- ranking them for field relevance in computational drug discovery, cheminformatics, generative chemistry, QSAR/ADMET, uncertainty quantification, Bayesian optimization, active learning, and molecular representation learning
- extracting evidence-rich snippets instead of feeding whole papers to an LLM
- generating short structured summaries locally
- turning the result into a publishable research digest

The goal is not to replace careful reading. The goal is to make paper triage faster, more systematic, and easier to publish.

## Example Output

The repository already contains generated digest pages you can inspect directly:

- [Latest archived digest](docs/posts/2026-04-06.html)
- [Older digest example](docs/posts/2026-03-15.html)
- [Archive index](docs/index.html)

Typical output includes:

- one highlighted "must read" paper
- short structured summaries for featured papers
- an editorial weekly narrative
- an archive page linking all generated digests

## What The Pipeline Does

1. Fetches recent papers from `arXiv`, `PubMed`, and `ChemRxiv`
2. Tracks new versus previously seen papers against a local archive
3. Filters papers using field-focused topic signals, keywords, and embeddings
4. Downloads PDFs for the most promising papers when available
5. Falls back to abstract-only processing when a PDF cannot be retrieved
6. Extracts section text and ranks evidence-bearing sentences
7. Sanitizes extracted text before it reaches the LLM
8. Summarizes only the most relevant snippets with a local `Ollama` model
9. Falls back to extractive summaries if the local LLM runner fails
10. Builds a weekly narrative and a professional HTML digest
11. Writes output to `docs/` for easy deployment with `GitHub Pages`

## Current Architecture

### Source retrieval
- [fetch_arxiv.py](src/fetch_arxiv.py) retrieves recent arXiv papers with rate-limit-aware settings
- [fetch_pubmed.py](src/fetch_pubmed.py) queries PubMed and reconstructs structured abstracts
- [fetch_chemrxiv.py](src/fetch_chemrxiv.py) tries the native ChemRxiv feed first and falls back to Crossref when ChemRxiv blocks scripted requests

### Relevance filtering
- [filter_papers.py](src/filter_papers.py) scores field relevance rather than scientific merit
- [research_taxonomy.py](src/research_taxonomy.py) centralizes the keyword taxonomy used across fetching, topic mapping, and ranking
- [topics.py](src/topics.py) maps papers into the target research areas such as drug discovery, computational chemistry, uncertainty, and molecular representation learning
- [paper_scoring.py](src/paper_scoring.py) ranks the final digest entries

### PDF processing and evidence selection
- [download_pdfs.py](src/download_pdfs.py) downloads PDFs with basic content-type validation
- [pdf_extract.py](src/pdf_extract.py) extracts and cleans raw text
- [pdf_sections.py](src/pdf_sections.py) segments important sections such as abstract, results, and conclusion
- [clean_sentences.py](src/clean_sentences.py) removes noisy or reference-like sentences
- [sentence_ranker.py](src/sentence_ranker.py) ranks sentences using embeddings
- [evidence_selector.py](src/evidence_selector.py) builds the compact evidence payload used for summarization

### Local summarization and safety
- [llm_summarizer.py](src/llm_summarizer.py) generates structured summaries with `Ollama` and falls back to extractive summaries when the local runner fails
- [generate_narrative.py](src/generate_narrative.py) writes the digest-wide editorial overview
- [security.py](src/security.py) strips obvious prompt-injection patterns from extracted PDF content before LLM use

### Publishing layer
- [generate_digest.py](src/generate_digest.py) turns summaries into HTML sections
- [blog_template.py](src/blog_template.py) provides the science-oriented blog shell used for both digest pages and the archive homepage
- [run_pipeline.py](src/run_pipeline.py) orchestrates the end-to-end workflow

### Utilities
- [deduplicate_papers.py](src/deduplicate_papers.py) maintains a local URL archive between runs without blocking digest rebuilds
- [utils.py](src/utils.py) handles JSON persistence and recovers safely from empty or invalid JSON files
- [embeddings.py](src/embeddings.py) centralizes the shared sentence-transformer backend and provides a lightweight hashed-vector fallback
- [config.py](src/config.py) keeps runtime knobs in one place

## Why The Pipeline Is More Robust Now

The original bottleneck was sending too much text to the local model and relying on brittle single-path processing.

The current version is faster and more stable because it:

- removes per-paper LLM scoring from the hot path
- reuses a shared embedding model instead of reinitializing multiple times
- selects only evidence-rich sentences from key sections
- summarizes the selected evidence instead of full paper text
- falls back to abstract-only processing when PDFs are missing
- keeps hallucination QA optional through configuration
- falls back to extractive summaries when `Ollama` returns runner errors
- rebuilds the digest even when a rerun finds no brand-new paper URLs
- tolerates empty or malformed local JSON cache files instead of crashing

This gives a better cost-quality tradeoff and makes local runs much less brittle.

## Design Goals

- local-first summarization rather than hosted black-box inference
- transparent heuristics that can be tuned by a scientist or engineer
- graceful degradation when one source or one stage fails
- output that is useful for both personal review and public publishing

## Prompt-Injection And Safety

Fetched PDFs and abstract text should be treated as untrusted input.

This repository now includes basic prompt-injection defenses:

- suspicious lines are filtered before they are passed to the LLM
- prompts explicitly instruct the model to ignore commands contained in source text
- summarization is grounded in extracted evidence snippets rather than full raw documents
- the optional QA stage can flag potentially unsupported claims

This is not a complete security sandbox, but it meaningfully reduces the risk of naive prompt-following on hostile paper content.

## Source Notes

### ChemRxiv

ChemRxiv is the least stable source in practice because direct RSS access is often blocked for scripted clients.

The current fetch order is:

1. native ChemRxiv RSS
2. Crossref lookup for recent ChemRxiv DOIs with prefix `10.26434`
3. Cambridge Open Engage feed fallback

This means ChemRxiv retrieval can still work even when the original RSS endpoint is blocked.

### PubMed

PubMed is used mainly for recent abstracts and review-like biomedical papers. The pipeline still filters those results aggressively so only papers with clear target-field relevance survive.

## Project Outputs

Running the pipeline produces:

- `data/raw_papers.json` for freshly fetched papers
- `data/filtered_papers.json` for relevance-filtered candidates
- `data/paper_sentences.json` for processed featured-paper evidence
- `data/summaries.json` for final ranked summaries
- `docs/posts/YYYY-MM-DD.html` for the weekly digest
- `docs/index.html` for the archive page

## Repository Snapshot

```text
src/
  fetch_*.py              source adapters
  filter_papers.py        field-focused triage
  pdf_*.py                PDF extraction and section handling
  evidence_selector.py    evidence ranking and selection
  llm_summarizer.py       local summarization + fallbacks
  generate_digest.py      digest rendering
  blog_template.py        GitHub Pages-ready layout
  run_pipeline.py         end-to-end orchestration

data/
  raw_papers.json
  filtered_papers.json
  paper_sentences.json
  summaries.json

docs/
  index.html
  posts/
```

## Setup

### Requirements
- Python `3.10+`
- A local `Ollama` installation
- An Ollama model such as `mistral`
- Optional fallback models such as `llama3.2:3b` and `tinyllama`

### Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull mistral
ollama pull llama3.2:3b
```

Optional environment variables:

```powershell
$env:OLLAMA_MODEL="mistral"
$env:OLLAMA_FALLBACK_MODEL="llama3.2:3b"
$env:OLLAMA_SECONDARY_FALLBACK_MODEL="tinyllama"
$env:ENABLE_SUMMARY_QA="false"
$env:ENTREZ_EMAIL="you@example.com"
$env:PROCESS_ALL_WHEN_NO_NEW="true"
```

The runtime now keeps `mistral` as the primary local model by default and will step down to installed fallback models if Ollama reports a memory-pressure error or a configured fallback model is missing. You can override the full ladder with `OLLAMA_MODEL_CANDIDATES`, for example `mistral,llama3.2:3b,tinyllama`.

## Running The Pipeline

```powershell
.venv\Scripts\python src/run_pipeline.py
```

If all sources and the local LLM are available, the digest HTML will be written under `docs/posts/` and the archive page will be rebuilt at `docs/index.html`.

On reruns, if there are no new URLs in the archive, the pipeline can still rebuild the digest from the current fetched set instead of halting.

## Testing

Unit and smoke tests use `pytest`.

```powershell
.venv\Scripts\python -m pytest -q
```

The test suite currently covers:

- prompt-injection sanitization
- evidence selection behavior
- PDF cleaning and section extraction
- fetcher parsing logic with mocked source responses
- ChemRxiv RSS and Crossref fallback behavior
- rendering helpers and blog output
- import smoke checks for the main source modules
- JSON recovery and deduplication edge cases

## Deployment

This repository is set up in a way that works well with `GitHub Pages`.

Typical deployment flow:

1. Run the pipeline locally or in CI
2. Commit the generated files in `docs/`
3. Configure `GitHub Pages` to serve from the `docs/` directory

## Why This Project Is Useful On GitHub

This repository is more than a scraper and more than a blog generator. It demonstrates how to combine:

- multi-source scientific retrieval
- domain-aware filtering
- evidence-grounded local summarization
- prompt-injection-aware text handling
- resilient fallback engineering
- automated static-site publishing

That combination makes it a strong example of a practical applied AI system rather than a toy demo.

## Customization Ideas

- change field weights in [filter_papers.py](src/filter_papers.py)
- expand target topic taxonomies in [topics.py](src/topics.py)
- tune evidence selection heuristics in [evidence_selector.py](src/evidence_selector.py)
- swap the local LLM model through `OLLAMA_MODEL`
- add new renderers for newsletters, Markdown exports, or JSON feeds

## Roadmap

- better section boundary detection for messy PDFs
- optional OCR fallback for image-heavy papers
- richer provenance in summaries, such as evidence-to-claim traceability
- CI automation for weekly digest generation
- source-specific adapters for publisher PDFs and supplementary metadata

## Project Pitch

If you care about molecular AI and drug discovery, this project is a practical way to turn scattered literature into a curated, publishable weekly briefing.

It is built for local-first summarization, transparent heuristics, and scientist-friendly output rather than black-box automation alone.
