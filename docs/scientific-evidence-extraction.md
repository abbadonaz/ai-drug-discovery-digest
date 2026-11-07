# Scientific PDF extraction and evidence selection (A15)

This opt-in path improves the traceability and composition of evidence sent to the existing summarizer. It does not verify claims, redesign the summary instructions, introduce a vector store or change literature ranking. **`legacy` remains the production default.** The previous extraction/section/cleaning/abstract-first code is retained for reproducible comparison.

## Architecture and compatibility

The legacy path is unchanged: `pdf_extract.extract_pdf_text()` flattens text, `pdf_sections.extract_sections()` finds keyword boundaries and truncates each section to `MAX_SECTION_CHARS` (5,000 by default), context assembly omits Methods, and summary selection fills slots from the abstract first. Legacy prompt limits remain 2,200 characters on the first attempt and 1,200 on retry. Its cleaning can remove table descriptions, citation fragments and numeric blocks; this behavior is retained only as the baseline.

The new path is:

1. `pdf_document.extract_pdf_document()` uses the existing pdfminer layout API to retain pages and text boxes. `prepare_document()` also accepts saved layout dictionaries, making backend comparison possible without changing selection.
2. `scientific_sections.detect_sections()` identifies line-anchored headings before flattening paragraph text. `build_passages()` intersects section spans with individual page text boxes.
3. `section_selection.select_passages()` ranks whole passages and allocates the evidence budget across complementary categories. Bibliographies, suspicious instruction text and ambiguous numeric blocks are excluded.
4. `FeaturedPaperEvidenceBuilder` retains the document, sections, candidate passages, selected evidence and diagnostics. Failed/low-quality extraction can use source-abstract passages. The usual minimum-evidence gate still applies: the section-aware path needs at least two selected passages totaling 160 text characters; otherwise the paper becomes a brief reference through the existing pipeline.
5. `build_summary_payload()` renders selected passages with ID, section and page labels. Both LLM attempts receive this same bounded evidence. Selected metadata is retained in `summaries.json` and the existing candidate provenance. Support remains `unverified`.

Public string-returning PDF extraction, existing dependency injection, legacy selector signatures, generation modes and publication interfaces remain available. The builder gains an optional `strategy` argument and an optional structured extractor dependency. Summary generation gains an optional keyword-only context limit; existing two-argument calls retain their behavior. Existing `SummaryRecord` permits the added metadata without removing any prior field.

## PDF layout and normalization

The adapter uses `pdfminer.high_level.extract_pages()` with `LAParams(boxes_flow=None)`. It sorts ordinary blocks top-to-bottom; simple left/right columns with a visible gutter are read column-by-column within bands separated by spanning blocks. Boxes are never concatenated across columns. Layout labels are `single_or_unknown`, `two_column_heuristic`, or `ambiguous`. This is a heuristic, not a guarantee of reading order.

Repeated identical margin boxes occurring on at least two pages and 60% of pages are excluded from normalized evidence. Margin-only page counters are also excluded. The margin rule uses the top/bottom 10% of page height. Raw text, bounding boxes and excluded blocks remain available for inspection. Running headers that vary by page, recurring scientific content in the margins and marginal notes require manual review.

Whitespace is normalized within lines while line boundaries remain available for heading detection. Visible line-end hyphens are removed only when the joined word belongs to a small explicit scientific-prose vocabulary (for example `molec-` + `ular`). Other alphabetic compounds retain the hyphen. Soft-hyphen line wraps are repaired. Numeric ranges and scientific punctuation are not reconstructed or reinterpreted. The normalized passage text can be compared to its retained source span and raw page block.

Extraction returns `success`, `low_quality` or `failed`; missing PDF inputs at the builder are `unavailable`. Low quality means very little text, a low alphabetic ratio or unresolved CID glyphs. These checks are warnings about usable extraction, not measures of scientific validity. Scanned PDFs, rotated text, equations, multi-column tables, floating sidebars, complex multi-column layouts and font encoding failures are not solved. No OCR dependency was added. The existing library was sufficient for the controlled single/two-column fixtures, not demonstrated to solve all publisher layouts.

## Section taxonomy

Recognized normalized categories are `abstract`, `introduction`, `methods`, `experimental_setup`, `datasets`, `model_architecture`, `training_validation`, `results`, `results_discussion`, `discussion`, `limitations`, `conclusion`, `supplementary`, `references`, and `unknown`.

Detection accepts exact known heading lines, numbered/Roman-numbered headings and known titles split over two adjacent lines (such as Materials and / Methods). A narrowly formatted numbered nested heading can inherit the preceding section category. Records distinguish `exact_heading`, `inherited_numbered_subsection` and `unknown`; these are rule descriptions, not calibrated confidence scores. An ordinary sentence containing “methods” or “results” is not a heading. Unrecognized unnumbered headings remain unknown or within their containing section; no universal publisher structure is assumed.

Sections contain `title`, `category`, `start`, `content_start`, `end`, `page_start`, `page_end`, `detection`, and `text`. Offsets are half-open Python character indices into the normalized document's `text`. Original PDF bytes and glyph positions are not character-index equivalent. Bibliography content remains inspectable but is excluded from selection by default.

## Passage contract and provenance

Candidate passages are dictionaries with:

| Field | Meaning |
| --- | --- |
| `passage_id`, `paper_id` | SHA-256-derived stable passage ID; paper URL/identifier |
| `source_type` | `pdf` or `abstract` |
| `section_title`, `section`, `section_detection` | Original heading, normalized category and detection rule |
| `page_start`, `page_end`, `block_id` | One-based PDF page and block identity; abstract pages are null |
| `start`, `end`, `source_text`, `text` | Document span and normalized display text; abstract offsets refer to the source abstract |
| `table_id` | Explicit textual table reference/caption identifier if found |
| `extraction_status`, `limitations` | Extraction status and known limitations |
| `support_status` | Always `unverified` |

PDF passages remain within a single text box/page, so page start/end coincide. Sections may span multiple pages. IDs depend on paper identifier, source type, span and text; unchanged input yields unchanged IDs. Changed extraction or document layout can change IDs and should be treated as a new evidence revision.

Selected passages add `evidence_id` (the passage ID), `score`, `selection_reasons`, `role`, and `summary_role` for existing consumers. The score is a transparent retrieval heuristic, **not scientific importance, factual support or confidence**. Prepared records retain `document`, `scientific_sections`, `passages`, `selected_evidence`, `selection_diagnostics` and `extraction_diagnostics`. Summaries retain the selected evidence and both diagnostic records, not a copy of the entire PDF document. Existing claim associations preserve page/section/span fields but remain positional associations, never verified support.

## Selection policy and configuration

Selection combines section priors with bounded binary features: metric-plus-number, validation/protocol cues, comparison cues, caveats and computational molecular-domain cues. Results, Methods and limitations receive larger section priors than generic introduction text. These features do not establish scientific relevance on their own. All weights and the coverage order can be supplied through the typed `SelectionSettings` API; no new embedding model is required.

The default coverage order is Methods, Results, limitations, abstract, discussion, followed by remaining ranked passages. Subsections such as datasets and training/validation count as Methods; Results and Discussion counts as Results for allocation/reporting. Near duplicates use token-set overlap (default 0.85), but passages with different numeric sequences are not collapsed. Text length is not the ranking objective.

Whole passages, including labels/separators, must fit the budget. Long passages are skipped with budget diagnostics rather than cut through a number or qualifier. Thus a small budget or oversized text box may omit important categories; `missing_coverage` reports this explicitly. The selector does not fabricate a shortened scientific result to make it fit.

```powershell
# Default: previous extraction and abstract-first selection
$env:EVIDENCE_SELECTION_STRATEGY = "legacy"

# Explicit opt-in for a controlled run
$env:EVIDENCE_SELECTION_STRATEGY = "section_aware"
$env:EVIDENCE_CHAR_BUDGET = "3600"
$env:EVIDENCE_MAX_PASSAGES = "6"
```

The evidence budget must be positive and no greater than `MAX_SUMMARY_CONTEXT_CHARS` (default 6,000). It includes evidence labels, excludes the fixed instruction/title overhead and is a **character budget, not a tokenizer guarantee**. Keep headroom for the model's instructions and generated tokens. Both prompt attempts preserve the selected section-aware evidence instead of silently applying legacy 2,200/1,200-character truncation. There is no model-context auto-detection in this milestone. Raising the limit may exceed a small model's actual capacity; lower it or configure an appropriate model context. Existing fallback summaries and their generation-mode labels remain intact; extractive fallback still has its prior sentence/length limits.

`evidence_mode` continues to describe prepared availability: `pdf_full_text`, `abstract_only`, or `unknown`. The comparison separately reports the mode of **selected** evidence. A prepared full-text record can still select only abstract passages under a restrictive budget; metadata must not be read as proof that full text supported a claim.

## Conservative table handling

The legacy cleaner rejects sentences mentioning tables. The section-aware path retains captions and nearby prose in their original blocks, including table identifiers, metric names, dataset/baseline context and numerical comparisons when those appear together in text. It never joins arbitrary column tokens into a result. Numeric-heavy ambiguous blocks are retained among candidates with `ambiguous_numeric_block` and excluded from the prompt. Every document records `table_cells_not_reconstructed`. Prose/table references do not prove table alignment is correct; no table-understanding system or inferred cell values are introduced.

## Offline comparison and replay

Two redistributable, entirely synthetic PDFs live under `tests/fixtures/evidence/`: a three-page scientific study with a two-column page and a single-page abstract-only document. `make_pdf.py` rebuilds them with standard-library code. All names, numbers and scientific statements are fictional test data. No real scientific results are fabricated or labeled verified.

```powershell
$env:PYTHONHASHSEED = "0"
$env:HF_HUB_OFFLINE = "1"
python -m evaluation.evidence_comparison --papers tests/fixtures/evidence/papers.json --benchmark tests/fixtures/scientific/benchmark.json
python -m pytest -q tests/test_scientific_evidence.py tests/test_evidence_selector.py tests/test_pdf_extract.py tests/test_summary_transparency.py
```

The manifest accepts saved `title`, `url`, `abstract`, `pdf_path` and optional benchmark `case_id`. Paths are relative to the invocation directory. The comparison reads each identical PDF for both strategies, pins legacy embeddings to the existing hashed fallback and makes no inference/download calls. `PYTHONHASHSEED=0` is required for reproducibility across processes because the legacy fallback uses Python hashing; the report records this setting. This milestone does not change that algorithm.

Reports contain source hashes, page/section/candidate counts, category distributions and proportions, metric-plus-number passage counts, lengths, extraction/selection failures, selected evidence-mode counts, diagnostics and full selected passages. Optional matching PR #5 cases produce explicitly labeled exact-statement **evidence** coverage proxies, not summary accuracy. No matched human-verified real case means `scientific_comparison=pending_human_verified_cases`. Synthetic differences cannot establish real-world improvement.

The regression replay blocks network/inference, runs both strategies through `ResearchDigestPipeline`, and publishes into separate temporary directories. It verifies the manifest, saved summary metadata, extractive generation mode and unverified provenance. PR #5 can read those summaries, but unmatched real/scientific annotations correctly produce no authoritative score. Production caches, historical digests and audit artifacts are not touched.

## Remaining limitations

Real-paper scientific improvement remains pending a reviewed corpus. The major remaining risks are layout misordering, headings that the taxonomy does not recognize, noisy PDF glyph extraction, oversized blocks, ambiguous tables, section/keyword biases, and budget-driven omissions. A selected passage is not an entailed claim. A16 and A02 work is not implemented here; neither the LLM's scientific instructions nor its claim verification is redesigned.

## Measured fixture results

`docs/scientific-evidence-comparison.json` stores the reproducible comparison, including PDF hashes and selected passages. The full-text synthetic fixture yields 3 pages, 9 sections and 12 candidates (including source-abstract candidates). Legacy selects 3 abstract passages, 0 metric-plus-number passages and 360 prompt-input characters. Section-aware selection selects 1 Methods, 2 Results, 1 limitations, 1 abstract and 1 discussion passage, including 3 metric-plus-number passages, within 1,197 prompt-input characters. Its table caption remains available; ambiguous numeric rows and the bibliography are excluded.

The abstract-only PDF yields 1 page, 1 section and 4 candidates. Both modes select 3 abstract passages after duplicate suppression; the section-aware input is 431 characters including traceability labels. Neither fixture reports an extraction or selection failure. Selected modes are two abstract-only cases for legacy versus one full-text and one abstract-only case for section-aware. Both fixtures are synthetic and have no matched human-verified annotation: these are composition/traceability results, **not evidence of improved scientific summary accuracy**.

Validation: the focused evidence/transparency tests plus `tests/test_scientific_evaluation.py` passed **103 tests**. The full suite passed **342 tests**. Temporary-directory publication replays passed for both strategies with network and inference blocked. Both LLM prompt attempts were captured and checked for selected Methods/Results/limitations; a separate >2,200-character test verifies the new budget is not silently truncated to the legacy limits. PDF fixtures are marked binary in their local `.gitattributes`; staged bytes and report hashes were checked against the tested originals.
