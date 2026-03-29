# AI Drug Discovery Digest

A sophisticated weekly research briefing system for drug discovery, cheminformatics, computational chemistry, and molecular machine learning. Automatically fetches, filters, and summarizes cutting-edge papers with intelligent two-stage LLM summarization and hallucination detection.

---

## Pipeline Architecture

```
1. Fetch & Deduplicate
   ├─ arXiv papers (drug discovery, cheminformatics, molecular ML)
   ├─ PubMed papers (drug discovery terms)
   └─ ChemRxiv papers (computational chemistry)

2. Filter & Rank
   ├─ Semantic similarity + keyword scoring
   └─ Topic classification (8 domains)

3. Deep Processing (Top 12 papers)
   ├─ PDF download + text extraction
   ├─ Section extraction (abstract, intro, methods, results, conclusion)
   ├─ Ranked sentence extraction
   └─ Two-stage LLM summarization + QA hallucination check

4. Light Processing (Papers 13–25)
   ├─ Metadata only (title, URL, topic)
   └─ Brief references (no PDF processing)

5. Generate Weekly Digest
   ├─ "Must Read" highlight (#1 paper, prominent display)
   ├─ Weekly Insights (trend narrative from top 12)
   ├─ Featured Summaries (papers #2–12, organized by topic)
   └─ Optional References (brief links to papers #13–25)

6. Render & Deploy
   └─ Modern, responsive HTML digest
```

---

## Key Elements

### "Must Read" Selection
- Top-ranked paper prominently featured
- Compelling visuals: gradient badges, action buttons, full summary
- Designed to guide domain experts to the highest-impact paper

### Two-Stage Intelligent Summarization
- **Stage 1**: Per-section LLM summaries (abstract, methods, results, etc.)
- **Stage 2**: Full-paper synthesis from top sentences + section summaries
- **QA Check**: Hallucination detection flags potential unsupported claims

### Tiered Processing
- **Featured (1–12)**: Deep PDF extraction + two-stage summarization + QA
- **Optional (13–25)**: Lightweight metadata references (fast)
- Reduces runtime by ~60% while maintaining quality for top papers

### 🏷 Smart Topic Classification
- 8 research domains (Docking, QSAR, Bayesian Optimization, Generative Chemistry, etc.)
- Keyword-weighted scoring system
- Organized visual grouping in digest

### Quality Control
- Two-stage summarization reduces hallucination risk
- Extractive + abstractive hybrid approach
- Optional papers prevent information overload

---

## Configuration

**Core Settings:**
- Featured tier: **top 12 papers** (full processing)
- Optional tier: **papers 13–25** (brief references)
- LLM model: **mistral** (via Ollama)
- Chunk size: **3500 tokens** with 250-token overlap

**Keywords added (March 29, 2026):**
- `active learning`
- `fep` / `fep calculation` / `free energy perturbation`

---

## Usage

### Setup
```powershell
# Install dependencies
python -m pip install -r requirements.txt

# Ensure Ollama is running
# ollama pull mistral

# Activate environment
.venv\Scripts\Activate.ps1
```

### Run Pipeline
```powershell
python src/run_pipeline.py
```

Outputs:
- `data/summaries.json` — Final ranked summaries + metadata
- `docs/posts/{date}.html` — Weekly digest HTML
- `docs/index.html` — Homepage with links to all digests

---

## Codebase Structure

**Core Modules:**
- `run_pipeline.py` — Orchestrates entire workflow
- `llm_summarizer.py` — Two-stage summarization + hallucination QA
- `generate_digest.py` — Renders HTML with "Must Read" structure
- `blog_template.py` — Modern, responsive CSS template
- `generate_narrative.py` — Creates weekly trend narrative

**Data Processing:**
- `fetch_arxiv.py`, `fetch_pubmed.py`, `fetch_chemrxiv.py` — Paper sources
- `filter_papers.py` — Semantic + keyword-based filtering
- `pdf_extract.py` — PDF text extraction & sentence splitting
- `pdf_sections.py` — Structures PDF text by sections
- `sentence_ranker.py` — Ranks informative sentences
- `clean_sentences.py` — Deduplication & noise removal

**Utilities:**
- `topics.py` — Domain classification keywords
- `paper_scoring.py` — Paper ranking algorithm
- `deduplicate_papers.py` — Weekly deduplication
- `download_pdfs.py` — Reliable PDF retrieval
- `utils.py` — JSON I/O helpers

---

## Tuning Quality

### Improve Filtering
- Adjust `POSITIVE_KEYWORDS` weights in `filter_papers.py`
- Add domain-specific keywords to `topics.py`

### Enhance Summaries
- Edit prompt templates in `llm_summarizer.py`
- Adjust `truncate_text()` max_chars for context size
- Lower hallucination check sensitivity if false positives occur

### Scale Processing
- Increase featured tier: modify `filtered[:12]` in `run_pipeline.py`
- Adjust optional tier: modify `filtered[12:25]` in `run_pipeline.py`

---

## Design Highlights

### Blog Template (SOTA)
- **Modern color scheme**: teal primary, purple accent
- **Visual hierarchy**: gradients, badges, responsive grid
- **User experience**: smooth transitions, hover effects, clear CTAs
- **Typography**: system fonts, optimized line-height and spacing
- **Responsive**: mobile-first, adapts to tablets and desktop
- **Accessibility**: semantic HTML, high contrast ratios

### Digest Structure
1. **Header** — Publication branding & date
2. **Must Read** — #1 paper with prominent styling & action buttons
3. **Insights** — Weekly trend narrative (extracted from top 12)
4. **Featured** — Papers #2–12 in responsive grid by topic
5. **Optional** — Brief links to papers #13–25
6. **Footer** — Attribution & source links

---

## Hallucination Safety

The pipeline includes QA checks to flag unsupported claims:

```python
check_result = hallucination_check(summary_text, source_text)
# Returns: "VALID" or "POTENTIAL_HALLUCINATION: [claim1, claim2, ...]"
```

If potential hallucinations are detected, a warning is appended to the summary.

---

## Next Steps & Recommendations

1. **Add overlap detection**: Identify genuinely novel findings week-to-week
2. **Enhance QA**: Fine-tune hallucination detection for scientific text
3. **OCR fallback**: Add Tesseract for scanned/image PDFs
4. **Custom model**: Fine-tune Mistral on drug discovery papers
5. **Historical analysis**: Track trends across months
6. **Notification system**: Email or Slack weekly digest

---

## Author & License

Created by **abbadonaz** | March 29, 2026
Curated from arXiv, PubMed, and ChemRxiv | Powered by Ollama + Mistral


