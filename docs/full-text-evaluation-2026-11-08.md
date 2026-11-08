# Three-paper full-text-first evaluation — November 8, 2026

This is a controlled convenience-sample replay and an agent inspection of source text, not a human-adjudicated scientific benchmark. Original results were preserved byte-for-byte. Exactly three new inference requests were authorized: KolTa structured, CAGenMol legacy, and CAGenMol structured. The run inventory below distinguishes raw model responses from accepted summaries and extractive fallbacks. A completed request is not necessarily a valid or scientifically adequate summary.

## Sources and reproducibility

The fixed article versions are [Tabular foundation models](https://arxiv.org/abs/2604.16123v1), [KolTa](https://arxiv.org/abs/2611.06394v1), and [CAGenMol](https://arxiv.org/abs/2604.11483v1). The local run root is `.evaluation-runs/fulltext-2026-11-08/`, outside production and excluded from Git. It contains `original/`, copied PDF `inputs/`, `provenance.json`, `original-result-metadata.json`, `model-inventory.json`, historical Ollama logs, extracted page/block text, and immutable per-condition `results/`. Original temporary files were retained. The copy manifest records original paths, modification times and SHA-256 hashes; result inventories bind new outputs to PDF hashes.

New requests used local `mistral:latest`, temperature 0.2, and `num_predict=900`, sequentially, with `PYTHONHASHSEED=0` and `HF_HUB_OFFLINE=1`. Embedding-model loading was patched to the deterministic hashed fallback for legacy selection. The installed model digest is `6577803aa9a036369e481d648a2baebb381ebc6e897f2bb9a766a2aa7bfbc1cf` (7.2B, Q4_K_M). Historical parameter settings are supported by the recovered replay source/documentation; original legacy files lack returned model metadata and raw responses. The historical weight digest and exact client timings were not recorded. Approximate server durations can be associated with original file completion times, but do not establish exact wall times or token counts.

Evidence selection and prompt format deliberately differ between conditions. The replay does not isolate which of those changes causes an observed difference. Each condition has one stochastic generation. The recovery limits each missing condition to one request, so a rejected legacy response cannot trigger an additional compact-prompt generation. The normal legacy production implementation still supports its existing compact retry. No inference output was regenerated to improve these results.

## Tabular foundation models

**Method and named entities.** The legacy output describes in-context prediction without task-specific training but names no concrete model version or benchmark. The structured output identifies TabPFN-2.6, TabICLv2, CheMeleon, MoleculeACE and Polaris and distinguishes original train/test splits and repeated random seeds. Its main methods reference is PDF page 14, passage `Pedf5b6408b60568ada91`.

**Validation.** The selected passage specifies reuse of original benchmark splits and five random seeds. Seeds describe stochastic repetition, not independent external validation. The structured output's statement that no task-specific hyperparameter optimization is performed drops the source's qualifier that this statement concerns the classical tabular ML models. This is a qualification loss; valid IDs do not resolve it. Neither output establishes prospective laboratory validation.

**Quantitative findings.** Neither output communicates an effect size. The article does: PDF page 4 reports 50/58 tasks and an 86.2% win rate (`P8f5c1c22cf2af97cd981`); page 6 gives CPU speedups of 4.8–27.3 times and GPU speedups of 18.3–46.0 times (`Pd32a2adfd3963ba7a8e7`). These values were extracted but not selected. The article's win definition includes statistically tied methods; it must not be described as strict superiority on every task. The selected abstract on PDF page 1 (`P0c9aa71737651dd26a78`) includes up to 100% win rates on 30 MoleculeACE tasks, but the structured output omits that supplied quantitative finding. Its quantitative section describes metrics and points to a table rather than giving results.

**Limitations.** Both outputs omit substantive limitations. PDF page 11 discusses scaling, memory/disk constraints and extensions beyond primarily single-molecule tasks (`P07eccf49ef731bff3721`); page 12 discusses single-task modeling and fixed representations (`P3926c7ebbcd52ab3bea6`). These passages were extracted but not selected. Therefore the structured output's unavailable-limitations label describes its selected context, not absence of limitations in the article.

**Coverage and unsupported claims.** The legacy input uses three abstract snippets without page locations. The structured input uses four page-traceable passages on pages 1, 9 and 14, including methods and results. Five of its six fields contain referenced text, but this is structural coverage only. Its favorable performance language is associated with article passages; the comparison does not independently verify the authors' experiments or scientific conclusions. The legacy claim that the paper provides no specific quantitative comparisons or benchmark details overgeneralizes missing context to the whole article and is contradicted by the inspected source text.

## KolTa

**Method and named entities.** The preserved legacy summary names KolTa, the four application types and AULC, but omits the three-stage predictor, PRC-UCB, ensemble disagreement and out-of-fold calibration details. The new raw structured response adds aspects of acquisition but fails the reference contract: its relevance field includes a literal sentence instead of a supplied passage ID. No guessed reference repair was applied. The accepted artifact is consequently an explicitly labeled extractive fallback, containing a source abstract sentence in the research-question field and unavailable text in the other five fields. Its attempted model metadata remains separate from the fallback's generator metadata.

**Validation and quantitative findings in the source.** PDF page 5 describes formulation-grouped folds and a locked evaluation set (`P1f388cf5f14c136c8029`, `P8bd9f93719b0d835ec7f`); NIST, ILThermo and DiffMix use 80/20 assignment, while Drug has 2,159 discovery and 524 locked formulations. These are retrospective evaluations on measured or simulated tasks, not a newly demonstrated prospective laboratory campaign. PDF page 6 reports Drug AULC 0.738 and ILThermo 0.748 (`P5bf056f56e75c18c4840`), and Drug median query counts of 348 versus 424 for SolvGNN-UCB, a saving of 76 queries or approximately 18% (`Pdfe7147dbf31e16c34aa`). Those prose passages were extracted but never reached the structured prompt.

**Selected evidence and omissions.** The structured prompt supplied six abstract passages, including the 0.032 versus at least 0.056 worst-case AULC gaps and 75/78 paired wins. The raw response retained 0.032 but omitted the comparator gap and paired-win count. Its wording that seven of eight strategies are outperformed on every task exceeds the supplied statement about paired comparisons across tasks and seeds. Its validation field attaches a three-measured-task statement to a passage that does not itself state that count. The article reports that the GP-Greedy difference is not significant in the paired analysis; the raw response does not preserve that qualification. These are source/context inspection findings, not an annotated unsupported-claim rate. The retained fallback discards the raw response after the invalid reference.

**Limitations and provenance.** Page 8 explicitly states that temperature extrapolation was not evaluated and only temperature varies (`P4846c85bf29e78e64243`); this text is extracted but not supplied. Heading detection labels it `results`, illustrating a separate section-label failure. The 21-page PDF yields 94,335 text characters, but 48 `(cid:...)` markers cause the document adapter to mark the entire document `low_quality`. The production builder therefore rejects its full-text passages before selection. All six supplied passages are abstract-only, with no page locations. This attempt does not demonstrate full-text summarization despite successful PDF retrieval.

## CAGenMol

**Method and named entities.** The raw legacy response names CAGenMol and condition-aware diffusion, but omits specific components and benchmark names. PDF pages 2–3 describe the Unified Constraint Adaptor, Step-PPO, Evolutionary Fragment Optimization, SAFE and the pretrained GenMol backbone. PDF page 6 describes CrossDocked2020, approximately 100,000 training complexes and 100 held-out target pockets (`Pd794a677dd7666271915`). Page 8 describes MiniMol-based property predictions and pseudo-labels. These extracted details are needed to distinguish the method from generic conditional generation.

**Legacy acceptance and source claims.** The raw legacy response has five sentences and is rejected by the existing two-to-four-sentence quality check; no second compact-prompt inference was issued. Its claim that the article lacks quantitative results is contradicted by the source. The retained extractive fallback reproduces broad favorable source statements, without numerical findings or uncertainty qualifications. Such extracted language is still unverified and is not evidence of measured biological binding or safety.

**Quantitative findings and validation in the source.** Page 7 reports a 69.7% computational success rate (`P76ca90e79a14507db6e5`). The prose describes improvement over a baseline, but this review does not reconstruct table-cell comparisons or relabel an ambiguous percentage as percentage points. The same page defines success using Vina, QED and SA thresholds, generates 100 molecules per test pocket, and distinguishes the structure benchmark from EFO-enhanced experiments. Page 6 explains AutoDock Vina as a computational score, while page 8 identifies predicted ADMET properties. These are computational evaluations and surrogate predictions; they do not establish synthesized-compound activity, clinical safety or experimental binding affinity.

**Limitations and coverage.** Page 9 explicitly notes limited compute and reliance on ESM-2, AutoDock Vina and MiniMol predictions without accounting for potential prediction errors (`Pa6ad3e747717150c8318`). The full-text parser obtains 71,665 characters from 19 pages, but 28 `(cid:...)` markers trigger document-level rejection. Many experiment/result blocks are also conservatively inherited as `methods`; passage categories are not authoritative article section labels. The raw structured response and retained artifact are detailed in the run inventory below.

**Structured result.** The new structured output is accepted as `llm`, with four fields containing referenced text, but its entire labeled evidence input is only 232 characters: one incomplete 182-character abstract fragment. The legacy abstract splitter stops at the first body occurrence of “methods,” splitting the abstract mid-sentence. It supplies no experiment, dataset or numerical finding. Nevertheless, the accepted validation field asserts evaluation on a small-molecule dataset; that assertion is not supported by the supplied passage. Its broad methodological description draws on the title without a methodological source passage. The raw limitations field incorrectly says the article discusses no limitations; because it has no references, the parser replaces it with the unavailable-evidence sentinel. Thus one unsupported absence claim is suppressed, while other unsupported prose passes. Quantitative findings, named benchmarks, held-out pockets, prediction uncertainty and actual article limitations are omitted. This is a contract-valid but scientifically inadequate abstract-only output.

## Where information was lost

| Stage | What this inspection can establish |
|---|---|
| Absent from the original article | No missing-summary item was established to be absent from the whole article. In particular, absent selected evidence is not proof of absent author reporting. Uninspected supplements, images and experimental claims remain unassessed. |
| Present in PDF but not extracted | No complete missing fact was conclusively established at this stage by visual page adjudication. Layout, mathematical symbols and table relationships are not reliably reconstructed; raw text may contain numeric cells without dependable scientific associations. This remains an extraction limitation, not a measured zero-loss result. |
| Extracted but rejected before selection | Readable KolTa and CAGenMol prose is present in the page/block extraction artifacts, but the document-wide `(cid:...)` gate rejects it. Their full-text validation, quantitative findings and limitations cannot reach the model through this path. |
| Extracted but not selected | Tabular numerical comparisons, speedups and limitations are present in identified passages but excluded from its four selected passages. Long blocks and a 3,600-character budget constrain coverage. |
| Supplied but omitted or distorted | Tabular's selected abstract includes a numerical win result omitted from its summary. KolTa's selected abstract comparisons lose numerical detail and scope qualifications in the raw response; invalid references then trigger wholesale fallback. CAGenMol's condition-specific omissions are documented with its exact selected evidence in the inventory. |

The extraction artifacts also permit investigation of section detection and selection independently of the document quality gate. Such inspection must not silently bypass production gating when reporting what the LLM actually saw.

## Interpretation

The first paper shows greater methodological specificity and page traceability, with continued numerical and limitation omissions. The resumed papers expose document rejection and output-acceptance failures. This sample does not support a general scientific-quality improvement claim. Mechanical reference checks establish identifier membership, and numeric checks establish token presence; neither establishes entailment, correct units, comparator scope, experimental validity or absence of unsupported claims. No human-verified annotations, authoritative factuality score, statistical confidence interval or model-as-judge score was created.

The appropriate next scientific work is to evaluate the document-quality rule on symbol-heavy but readable PDFs, improve section detection and limitation/numerical coverage under a fixed budget, and then conduct a separately approved evaluation with source-adjudicated references. These experiments preserve the present failure evidence rather than silently tuning and regenerating this sample.


## Saved run inventory

| Paper / condition | Evidence chars | Selected / page-traceable | Referenced fields | Retained generation | Request seconds |
|---|---:|---:|---:|---|---:|
| paper-1-legacy | 592 | 3 / 0 | paragraph | llm | ~110 |
| paper-1-section_aware | 3584 | 4 / 4 | 5/6 | llm | ~400 |
| paper-2-legacy | 668 | 3 / 0 | paragraph | llm | ~90 |
| paper-2-section_aware | 1344 | 6 / 0 | 1/6 | extractive_fallback | 311.14 |
| paper-3-legacy | 832 | 3 / 0 | paragraph | extractive_fallback | 118.62 |
| paper-3-section_aware | 232 | 1 / 0 | 4/6 | llm | 201.81 |

Evidence characters count labeled selection, not the entire prompt or PDF. Page-traceable counts describe selected passages, not verified claims. Referenced-field counts include extractive fallback fields and do not imply correctness. Original timings prefixed with ~ are rounded historical server durations; new values are measured client wall times. All three new responses ended normally before the 900-token cap; no output was truncated by that cap.

The local `inventory.json` records each result hash, actual selected passage IDs, page/section labels, timing and generation issues. `results/comparison.json` and `results/summaries.json` consolidate all six retained outputs. The scientific framework reports `evaluated_count=0` and `authoritative_benchmark_available=false` because these papers have no matching human-verified benchmark annotations.

## Final validation and preservation

- Focused regression suite: **76 passed in 13.62 seconds** (checkpoint/resume, retrieval, structured summaries, legacy summarization, saved legacy records, HTML rendering and provenance transparency).
- Full pytest suite: **371 passed in 77.23 seconds**. A preceding run passed 370 tests; the final count includes the added unavailable-evidence/no-model-call regression.
- Offline fixture harness: both expected relevant papers retrieved; both fixture summaries pass its quality checks. These are mechanical fixture checks, not a real-paper scientific validation score.
- All six saved summaries validate through `SummaryRecord`. An isolated HTML preview verifies unverified source-association labels, abstract-only warnings, model identity and fallback labels. Production HTML was not regenerated.
- Post-test hashes: **72/72 production files unchanged**, **9/9 publication-manifest artifacts unchanged**, all copied originals and original temporary artifacts unchanged, and all six result hashes stable.
- Exactly **three** new raw-response checkpoints and three HTTP-200 chat requests appear in the local Ollama log. No new HTTP 500, no repeated original generations, and no pending inference requests. Two conditions have rejected raw outputs and retained fallbacks; CAGenMol structured passes the contract but remains scientifically inadequate.
- `git diff --check` continues to report only the pre-existing generated `docs/archive.html:871` trailing whitespace. It was preserved. The implementation diff and newly written code/tests/docs introduce no whitespace errors; two untouched `.gitignore` whitespace lines already exist in HEAD.
- Local `change-scope.json` classifies all 40 modified/untracked files visible after recovery. Raw responses, evaluation JSON, copied PDFs and the HTML preview are isolated under ignored `.evaluation-runs/`. Existing production JSON, four untracked production PDFs, generated HTML and `docs/publication.json` remain outside the proposed implementation commit.

Changed during this recovery: `.gitignore`, `src/evaluation/checkpoint.py`, `src/evaluation/full_text_replay.py`, `tests/test_replay_checkpoint.py`, `docs/full-text-first-workflow.md`, and this report. The other production and implementation modifications predate this recovery.

Proposed commit scope, pending approval: the existing full-text retrieval/structured-summary implementation and focused tests, the checkpointed replay helper and its regression tests, and workflow/comparison documentation plus the isolated-run ignore rule. Exclude all production state, PDFs, generated publication files, local checkpoint pointers/hash snapshots, raw evaluation artifacts, and unrelated earlier audit/backlog documents. No files have been staged, committed or pushed. Keep production activation under review until the readable-PDF rejection, abstract truncation, numerical/limitation coverage and unsupported prose issues are addressed in separately reviewed work.


## Post-fix stabilization - separate from the original evaluation

Everything above this heading is the original pre-stabilization report and has been preserved byte-for-byte. Its snapshot is `.evaluation-runs/stabilization-2026-11-08/original-evaluation-report.md`. All 53 files in the completed evaluation directory retain their baseline hashes. This section reports deterministic cached-input/output checks, not another LLM evaluation. No original generation was rerun and no original result was rewritten.

### Root causes identified before edits and focused remedies

| Issue | Root cause | Stabilization |
|---|---|---|
| Readable PDFs rejected | A single `(cid:...)` occurrence vetoed the whole document. | Assess readable character/letter content and marker density; retain warnings and raw text. More than 10% marker characters still rejects the document. Unresolved glyph passages are excluded individually, without guessing symbols. |
| Abstract truncated | Legacy flat extraction stopped at the first prose keyword `methods`; the replay inherited that abstract. Page-column ordering and next-page continuation also matter. | Require heading-like boundaries in the legacy splitter. The section-aware builder and replay recover column-aware abstract blocks and a next-page continuation. Preserve full available abstract on the record; apply explicit selection budgets separately. |
| One invalid reference caused wholesale fallback | Reference validation raised on one bad ID before retaining other fields. | Withhold only affected sections, record issue codes and expose withheld-field counts in HTML. Never repair IDs by guessing. All-rejected or malformed output uses labeled extractive fallback, with attempted-model metadata separate from the fallback generator. |
| Results/limitations crowded out | Methods-first coverage, large unsplit blocks, incomplete metric signals, and headings/run-in labels inherited into the wrong category. | Prioritize reported numerical Results and explicit caveats, then Methods. Add AULC/success/query signals, distinguish reported outcomes from benchmark descriptions, split oversized prose at sentence ends (900 characters by default), retain exact source spans, and recognize observed run-in/headings. |
| Unsupported values/validation passed | Numeric tokens were pooled without unit/sign associations; any valid passage ID could carry unsupported prose. | Normalize numbers/signs and check common number-unit pairs. Withhold unsupported validation details, protocol-free validation claims, selected high-risk validation/significance claims and article-wide absence claims, with logged reasons. These remain conservative lexical checks. |

No framework or dependency was added. Existing summary keys, legacy string interfaces and six-section rendering remain available. Partial LLM acceptance is explicit; it is not extractive text mislabeled as generated analysis.

### Cached source coverage after stabilization

The final source-coverage check uses the actual section-aware builder with the saved layouts and source abstracts. Tabular is a selector control; KolTa and CAGenMol reproduce the observed failures. `targeted-pipeline-final.json` records the exact selected passages, page locations, budgets and quality diagnostics. Other intermediate files remain preserved under the stabilization directory.

| Paper | Original -> post-fix document status | Labeled input characters | Page-traceable selected passages | Explicit caveat passages selected |
|---|---|---:|---:|---:|
| Tabular foundation models | success -> success | 3,584 -> 3,591 | 4 -> 6 | 1 |
| KolTa | low_quality -> success | 1,344 -> 3,552 | 0 -> 5 | 1 |
| CAGenMol | low_quality -> success | 232 -> 3,574 | 0 -> 6 | 1 |

All contexts remain within the 3,600-character budget. Caveat counts require an explicit cue in addition to the category label; section labels alone are not scientific annotations. Other selected passages may still inherit imperfect labels.

CAGenMol's available abstract is now 1,303 characters rather than the earlier 182-character fragment. The saved code-availability ending is retained, and introduction prose is excluded. The Tabular abstract's page-2 continuation is retained, yielding 1,671 characters. KolTa retains its complete 1,572-character feed abstract. Complete source retention does not imply that every abstract sentence fits alongside full-text evidence; available and selected abstract character counts are recorded separately.

KolTa's context now includes page-6 query-efficiency prose (348 versus 424 comparator queries and approximately 18% savings), plus its page-8 temperature-extrapolation/temperature-only caveat. CAGenMol's context includes the page-7 69.7% computational success-rate passage and page-9 compute/prediction-error caveat. Tabular's context includes the page-10 relative-RMSE/runtime comparison and a page-11 scaling/multi-component caveat. These are author-reported source statements now available to generation, not newly verified scientific conclusions or claims that a new model output preserved them.

### Revalidation of cached model responses

The cached raw responses were checked against their **original** supplied evidence, separately from the new selections. Reusing old text with a different evidence set would confound this comparison; that was not done. `targeted-evaluation-stabilized.json` records this check and the implementation hashes.

- **KolTa:** its invalid relevance citation is withheld. Its claim about three measured tasks is also withheld because that detail is absent from its cited passage. Three other generated fields survive, rather than losing all six fields to a single malformed citation. This is partial acceptance of the old response, not a new generation or proof that those fields are factual.
- **CAGenMol:** the validation assertion about evaluation on a small-molecule dataset is withheld because its original problem-statement fragment supplies no protocol evidence. The limitations absence claim remains withheld. Three generated fields survive; their source associations remain unverified.
- Regression cases also reject changed concentration units, unsupported values, reversed docking-score signs, unsupported prospective/external validation and contradicted statistical-significance statements. A Unicode minus and a numerical range are retained when supported. An all-invalid response remains extractive fallback, with no LLM generator identity assigned to the extraction; attempted-model identity is retained separately.

No new LLM call was needed. Consequently this pass does not measure fresh-generation numerical completeness, new-prompt obedience or a general scientific-quality improvement. Some accepted cached prose still has weak methodological support or overbroad comparator scope; identifier and lexical guards cannot establish entailment.

### Final checks and commit readiness

- **106 focused tests passed in 13.10 seconds.** The actual observed layouts and raw outputs are represented in `tests/fixtures/stabilization/observed_failures.json`; this is an intentional regression fixture, not human scientific annotation or production state.
- **393 full-suite tests passed in 79.16 seconds**, including legacy compatibility, HTML/provenance labeling, source spans and checkpoint behavior.
- **72/72 production files, 9/9 publication-manifest artifacts and 53/53 completed evaluation files remain unchanged.** No new chat requests appear in Ollama's server log. No evaluation process remains running.
- Implementation/test whitespace checks pass. Whole-repository `git diff --check` still reports only the pre-existing generated `docs/archive.html:871` whitespace; the protected artifact was left untouched.
- Changes are limited to document/abstract extraction, section/passage selection, structured-summary guards and labels, replay abstract recovery, configuration, focused regression fixtures/tests and these workflow/report documents. No downloaded PDFs, production JSON/HTML/manifests, or local evaluation outputs belong in the proposed implementation commit.

The stabilization is ready for a reviewed commit, with these limitations disclosed. It is not a scientifically validated autonomous summarizer: marker/reading-order thresholds remain heuristics; unreadable glyph passages and oversized sentences can lose evidence; lexical guards can miss semantic errors or reject valid paraphrases; metric/dataset/comparator attribution and complex negation remain unresolved; fresh generation with improved evidence has not been measured. The original scientific evaluation remains non-authoritative without source-adjudicated annotations. No commit or push has been performed; approval is still required.
