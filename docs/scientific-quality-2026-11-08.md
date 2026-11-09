# Scientific summary quality: November 8, 2026

This evaluates the stabilized implementation at `c7ae1df` on `dev_az`, then a
targeted working-tree patch. These are **agent-assessed evidence-fidelity judgments,
not human-verified scientific accuracy**. The three convenience-sampled articles
and one stochastic response per condition cannot establish general model accuracy
or a statistically reliable improvement. Passage references establish navigation;
number matching supplies necessary checks, not factual entailment.

The original full-text and stabilization evaluations are unchanged. This milestone
uses `.evaluation-runs/scientific-quality-2026-11-08/`, outside publication paths.
Its `source-checklists.json` retains source excerpts, original PDF pages, passage
IDs and document hashes. `baseline-scorecard.json` and baseline outputs were frozen
before implementation changes; `baseline-frozen-hashes.json` records their hashes.
`baseline-assessment-errata.json` corrects the shorthand description of legacy
format rejection without overwriting that original assessment.

For review without the ignored local run, a [minimal reproducible evaluation
archive](../tests/fixtures/scientific/quality-2026-11-08/README.md) now includes the
rubric, checklists, scorecards, ten raw generation checkpoints, selected passages,
historical legacy output, final retained sections and provenance. Package integrity
and final parser/guard outcomes can be replayed offline through the focused tests.
This does not reproduce stochastic generations, source extraction or subjective
scientific scoring, and includes no PDFs or model caches.

## Rubric and baseline

The anchored ordinal scale applies to predefined essential facts: **0** absent,
contradicted or materially misleading; **1** partial with a material omission or
qualification error; **2** mostly faithful, minor omissions and no identified major
error; **3** faithful with sufficient essential coverage. An unresolved claim is
unassessed, not presumed correct. Consequential errors remain explicit below; no
aggregate mean is used to hide them.

O = objectives; M = methods and validation; Q = quantitative fidelity;
L = author caveats; U = unsupported-claim control; T = traceability; R = readability.
T concerns relevant source navigation, not scientific correctness. Scores describe
retained output unless explicitly labeled raw.

| Paper / baseline output | O | M | Q | L | U | T | R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tabular legacy, extractive fallback | 2 | 1 | 0 | 0 | 3 | 1 | 3 |
| Tabular full text | 2 | 1 | 0 | 2 | 1 | 2 | 2 |
| KolTa legacy, historical reused response | 2 | 1 | 1 | 0 | 2 | 1 | 3 |
| KolTa full text | 2 | 1 | 1 | 3 | 0 | 2 | 2 |
| CAGenMol legacy, extractive fallback | 2 | 1 | 0 | 0 | 1 | 1 | 2 |
| CAGenMol full text | 2 | 1 | 1 | 2 | 1 | 2 | 1 |

The raw Tabular and CAGenMol legacy responses both score U=0: they infer that
the articles lack concrete datasets/benchmark details from their selected abstract
context. The articles contain those details. Their raw responses and the actual
format-gate failures are retained, rather than counting the resulting extraction
as successful LLM analysis. Historical KolTa has an exact ordered legacy-evidence
match, but lacks the original raw prompt, raw response checkpoint and model digest;
those fields remain unknown. CAGenMol raw full-text validation cites the wrong
passages and is withheld, improving navigation in the retained output while losing
that section. Its numerical year occurs elsewhere in the supplied evidence, so
this is a citation/generation error, not missing article information.

| Condition | Labeled input characters | Generation seconds | Retained form / populated sections |
| --- | ---: | ---: | --- |
| Tabular legacy | 544 | 130.3 | extractive fallback |
| Tabular full text | 3,591 | 399.5 | LLM, 6/6 |
| KolTa legacy | 668 | unknown | historical LLM paragraph |
| KolTa full text | 3,552 | 414.5 | LLM, 6/6 |
| CAGenMol legacy | 771 | 101.8 | extractive fallback |
| CAGenMol full text | 3,574 | 443.4 | LLM, 5/6 |

All five planned fresh baseline calls completed sequentially, with raw responses
checkpointed before parsing and no repeated successful calls. The same local
`mistral:latest`, temperature 0.2 and 900-token cap were used. Installed digest:
`6577803aa9a036369e481d648a2baebb381ebc6e897f2bb9a766a2aa7bfbc1cf`.
Prompts and selected evidence differ deliberately between formats; timings include
prompt processing and generation and are not controlled performance benchmarks.
Legacy and structured formats also differ in permitted length and content. This
assesses the combined pipeline, not the causal effect of retrieval alone. The
agent assessment is not blinded and has no independent inter-rater agreement.

## Source checklist and loss diagnosis

All pages below are original PDF page indices, beginning at 1. Exact passage IDs,
excerpts and source hashes are retained in the isolated checklist. No human-reviewed
annotations or reconstructed table values were created.

| Article | Essential source facts and page references | Baseline loss or error |
| --- | --- | --- |
| Tabular | In-context molecular-property prediction, p1; TabPFN-CheMeleonFP 50/58 wins (86.2%), p4, where wins include statistical ties, p15 | Aggregate result extracted but not selected; supplied tie qualification omitted |
| Tabular | CPU 4.8–27.3× and GPU 18.3–46.0× speedups versus fine-tuned CheMeleon on representative Polaris datasets, p6 | Extracted but not selected |
| Tabular | Engineering Pareto comparison: approximately 10 percentage-point larger relative RMSE gap and order-of-magnitude slower fine-tuned baseline, p10 | Supplied but all effect sizes omitted; experimental scope lost |
| Tabular | TabPFN-2.6/TabICLv2; original splits, five seeds, p14; shared fixed test split measures model stochasticity rather than alternative-test-set uncertainty, p15 | Versions/splits not selected; supplied fixed-split qualification omitted |
| Tabular | Feature-dimensional scaling and single-molecule/mixture limitations, p11 | Mostly preserved; selected block ended with dangling “without” |
| KolTa | Three-stage predictor, PRC-UCB disagreement/physics residual, p1; formulation-grouped five-fold OOF calibration, p5 | Method blended with greedy ablation; OOF protocol not selected |
| KolTa | 80/20 pool/locked splits on three tasks, Drug 2,159/524 formulations; locked set only final prediction error, p5 | Supplied but omitted |
| KolTa | AULC 0.738 Drug, 0.748 ILThermo, first there and second on NIST/DiffMix; 75/78 paired wins against seven strategies; GP-Greedy difference not significant, p6 | Main paragraph not selected; generated superiority “on every task” is misleading |
| KolTa | Drug median 348 versus 424 SolvGNN-UCB queries to 80% macro active recall, 76/about 18% fewer; 86-drug task and batch interpolation, p6 | Extracted but not selected; supplied ablation numbers also omitted |
| KolTa | A significance criterion is conditional, not an observed p-value, p6; temperature-only, five fixed temperatures and unevaluated extrapolation, p8 | Criterion rendered as a result; caveats correctly retained |
| CAGenMol | UCA, Step-PPO and inference-time EFO are distinct, p2; architecture, p4 | UCA/training partly preserved; EFO role not explained |
| CAGenMol | CrossDocked2020 approximately 100,000 training complexes and 100 held-out pockets, p6; 100 molecules/pocket and computational Vina/QED/SA/diversity evaluation, p7 | Extracted but not selected |
| CAGenMol | 69.7% computational success rate, p7; source says over 16% baseline advantage | Value retained, scope missing; the ambiguous source phrase is not relabeled percentage points |
| CAGenMol | SFT then Step-PPO; EFO excluded in this benchmark, p7 | Supplied exclusion omitted |
| CAGenMol | Limited compute and unmodeled ESM-2/Vina/MiniMol prediction errors, p9 | Vague caveat; predicted Ames-negative outcomes overstated as toxicity avoidance |

No predefined essential prose fact was demonstrated absent from these articles or
unavailable in document extraction. Table-cell correctness remains unassessed.
Several PDF blocks end mid-sentence because segmentation follows layout blocks;
that is distinct from loss of the text from the retained document. Selection and
budget interact: relevant candidates exist, but six slots/3,600 characters are
spent on repeated abstract/discussion, ablations or favorable filler. Generation
then omits some facts that were supplied. Suppression is a separate final stage:
CAGenMol's retained validation is missing because its generated citations fail.

## Targeted implementation and reuse

The patch changes three affected modules; legacy generation and retrieval remain
intact. It reuses `SelectionSettings`, feature ranking, passage records and exact
offsets, the six-section schema, `SummaryRecord`, existing number/unit checks,
`CheckpointChat`, immutable `write_once` and the existing replay runner.

- Passage construction omits dangling tails when meaningful complete prose can be
  retained, labels omissions/incomplete blocks, and keeps raw document/abstract
  text. Short run-in labels alone do not trigger trimming of the evidence that
  follows them. This is conservative segmentation, not reconstruction.
- Selection prioritizes explicit non-significant comparisons and experimental
  protocols, discounts ablation repetition and reserves no mandatory slots for
  abstract/discussion repetition. Numerical architecture parameters no longer
  count as reported quantitative findings. Method weighting and evaluation-metric
  cues address the observed loss of CAGenMol's dataset/protocol/architecture.
  Favorable prose inherited under Limitations does not displace an actual caveat.
- The prompt explicitly requests scoped effect sizes, negative results, held-out
  procedures, component exclusions and named error sources. It distinguishes
  statistical thresholds from outcomes and predictions from demonstrated safety.
- Lexical guards flag the observed universal-superiority and threshold-as-result
  patterns. Significance polarity keeps supported negative findings and scopes
  explicit named negative comparisons separately from positive ones.

The first post-fix evaluation exposed two further failures before any retry:
KolTa and CAGenMol both exhausted the 900-token cap, yielding incomplete JSON.
Their initial attempts, raw responses, metadata and labeled extractive fallbacks
are frozen in `first-postfix-frozen-hashes.json`. This is an output-completeness
regression, not a successful LLM analysis. Their diagnosis files precede the
follow-up implementation. No HTTP/server failure occurred in those attempts.

The narrow follow-up replaces the permissive 80-word-per-section/uncapped-reference
instructions with short per-field limits and at most two relevant IDs. Negative
comparisons take precedence over secondary favorable results. A generic figure
caption had also displaced CAGenMol's architecture; caption filtering and a
structural-definition cue now preserve architecture, dataset, evaluation metrics
and the benchmark-specific training protocol together. A loose architecture-word
bonus was replaced with the more specific structural cue, rather than retained
as a competing scorer. The fixture includes the actual caption, alternate training
paragraph and GenMol paragraph that competed for that slot.

Clean-as-you-go changes cache feature signals once per candidate, remove repeated
feature extraction and repeated family computation, replace the superseded
significance branch with a cohesive statistical-check helper, and narrow the
broad fallback boundary to inference. Validation programming errors propagate;
malformed model output still has a labeled compatibility fallback. No dependency,
new architectural layer or extra runtime configuration flag was introduced.

## Post-fix evaluation and validation

All calls and targeted retries have finished. There were ten fresh calls: five
baseline, three first post-fix, and two retries of invalid outputs. All were
sequential. No successful generation was repeated; historical KolTa legacy and
all completed legacy controls were reused. No HTTP 500 occurred. Every raw response
and result remains preserved, including invalid attempts.

| Post-fix attempt | Input chars | Seconds | Raw completion / original parser outcome |
| --- | ---: | ---: | --- |
| Tabular, first patch | 3,481 | 460.5 | 766 tokens; LLM with relevance withheld |
| KolTa, first patch | 3,051 | 495.0 | 900 tokens; truncated JSON, extractive fallback |
| CAGenMol, first patch | 2,630 | 516.8 | 900 tokens; truncated JSON, extractive fallback |
| KolTa, compact retry | 3,051 | 425.8 | 652 tokens; complete JSON, malformed relevance entry, extractive fallback |
| CAGenMol, compact retry | 3,263 | 526.8 | 623 tokens; complete JSON, malformed relevance entry, extractive fallback |

Both compact responses omit `passage_ids` from relevance. The strict entry-shape
check aborted the entire response, unlike the existing per-field handling of
unknown IDs. A final narrow parser fix reuses per-field withholding for malformed
entries: it never guesses missing IDs. Top-level contract and malformed-JSON
failures remain strict. KolTa also incorrectly describes AULC as its formulation
ranking rule; a conservative necessary-support guard now withholds that observed
metric-as-acquisition claim. CAGenMol's method includes Eq. 11 but cites architecture
and metric passages instead of the supplied training protocol; the existing
new-number guard withholds it.

These final fixes were assessed against **cached raw responses with zero further
model calls**, saved separately in `cached-final/`. Original fallback results were
not overwritten or relabeled. The resulting partial generated outputs disclose
all withheld fields and retain `scientific_support_status=unverified`. Five fields
remain for Tabular, four for KolTa and four for CAGenMol. The original compact
responses are not valid complete six-field input contracts; normalized retained
outputs must not be confused with fully compliant raw generation.

The final CAGenMol context replaces filler with architecture; Tabular and KolTa
contexts are unchanged. Tabular is an earlier-prompt result, **not** a fresh test
of the compact prompt. The cached baseline guard replay separately flags KolTa's
original universal-superiority and threshold-as-result errors. Neither replay is
a fresh generation or scientific validation.

| Paper / retained post-fix output | O | M | Q | L | U | T | R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tabular, first-patch response through final guards | 2 | 1 | 1 | 2 | 1 | 2 | 1 |
| KolTa, compact response through final guards | 2 | 1 | 1 | 1 | 2 | 2 | 2 |
| CAGenMol, compact response through final guards | 2 | 1 | 1 | 2 | 1 | 2 | 2 |

`final-scientific-scorecard.json` retains raw/retained scores, source-page rationale,
generation metadata, loss attribution and regressions. These ordinal judgments
use the original rubric; they do not establish human-verified accuracy.

- **Tabular:** quantitative fidelity improves from 0 to 1: the response now gives
  50/58 wins, 86.2%, average rank 4.52, the 10 percentage-point relative RMSE gap
  and runtime difference. The model-stochasticity qualification also improves.
  Supplied ties-as-wins and 11-engineering-task scope are still omitted. Hardware
  speedups and model versions remain unselected. HSD detail is repeated in methods
  and validation, lowering readability; relevance is now withheld.
- **KolTa:** properly scoped first/second ranks and paired wins replace the
  misleading every-task superiority. Paired gains and 76-query/18% savings appear.
  The supplied non-significant GP-Greedy result, 80% recall condition, 348/424 counts
  and named query comparator remain omitted. OOF context is selected, but its
  grouping/fold details are lost in retained prose; locked-set split/design is
  displaced from baseline input. The raw AULC-as-acquisition error is withheld,
  leaving no generated methodology. Author-caveat fidelity regresses from 3 to 1:
  explicitly untested extrapolation, temperature-only scope and five fixed
  collocation temperatures are lost or weakened despite being supplied.
- **CAGenMol:** retained validation now includes 100 molecules/pocket and Vina,
  QED and SA. Architecture, dataset and protocol are supplied together, yet the
  model omits CrossDocked2020 and the 100,000/100 train/held-out counts. Incorrect
  method citations cause withholding. The 69.7% value remains correct but lacks
  benchmark scope; the source's over-16% comparison remains ambiguous. A former
  toxicity-avoidance assertion disappears, but broad dominance/robustness claims
  remain. Named predictor error sources and the benchmark-specific EFO exclusion
  remain missing or vague. Completeness falls from five retained fields to four.

The main remaining bottleneck is generation and citation allocation, with some
selection trade-offs still present. Better extraction/selection does not ensure
that supplied qualifications survive generation. The measurements show **mixed,
limited gains, not a demonstrated overall scientific-quality pass**. This should
not be committed as a completed scientific-quality milestone without review.

## Verification and review scope

The final focused suite passes **96 tests**; the full suite passes **412 tests in
76.68 seconds**. Legacy compatibility, missing/incomplete PDFs, abstract fallback,
number/unit/sign safeguards, source offsets and HTML provenance/withholding labels
are covered. Cached final outputs additionally check HTML withholding counts.
All 88 Python source/test files compile without producing bytecode. A simple AST
name-use check finds no unused imports in the affected Python files; this is not
a substitute for linting or type checking.

The repository has no configured formatter/linter/type checker, and ruff, black,
flake8, mypy and pycodestyle modules are absent from the virtual environment. No
new tool or dependency was installed. Intended tracked changes pass
`git diff --check`; new test/fixture/report files pass a direct whitespace scan.
The whole working-tree check still reports only the pre-existing generated-file
whitespace at `docs/archive.html:871`, which remains untouched.

Final hash checks confirm unchanged bytes for **72 production files**, all **nine
publication-manifest artifacts**, **76 prior evaluation files**, **14 frozen
baseline files**, **11 first post-fix files** and **10 compact-attempt files**.
The model digest is unchanged. Branch remains `dev_az`, HEAD `c7ae1df`; nothing is
staged, committed, pushed or merged. No published digest was regenerated.

The original review scope was six files: three source modules, the focused quality
test module, its minimal observed-failure/source-excerpt fixture, and this report.
Production changes already present at session start, PDFs, manifests, other
untracked documents, evaluation outputs and caches remain outside that scope.
The source-only diff is **+201/-44 lines** across three modules; the test, minimal
fixture and report are new files. `change-summary.json` records complete per-file
and total counts. Legacy implementation remains available for compatibility and
reproducibility; no competing replacement pipeline was added.

## Milestone finalization: November 9, 2026

The implementation was reviewed without further source changes. The authorized
commit scope adds the six small evaluation-archive files to the original patch;
production/publication files, PDFs, unrelated documents and the ignored run remain
outside that scope. The archive occupies approximately 229 KB and includes the
failed attempts as well as retained outputs. Four archive integrity/replay tests
were added to the existing quality test module, without a new runtime abstraction.

Fresh offline verification passes **23 quality tests in 64.77 seconds** and
**416 full-suite tests in 208.01 seconds**. Historical 96/412 results above remain
historical, not relabeled as this run. All 88 source/test Python files compile in
memory. The staged patch passes whitespace checks; the pre-existing production
HTML whitespace remains outside the commit. Preservation hashes still match all
72 production files, nine manifest artifacts, 76 prior evaluation files and all
14/11/10 frozen baseline/first-postfix/compact artifacts. No new model generation
or digest regeneration was performed.

Review also confirmed another lexical boundary: a significance assertion can pass
the statistical helper when its source only states a conditional p-value threshold.
The narrow existing threshold-as-outcome pattern does not cover that paraphrase.
This joins the archived attribution/direction false acceptances as an explicit
limitation; no new scientific relationship verifier is implemented in this patch.
The next offline experiment remains a proposal requiring review.

## Scientific limitations and technical debt

The source-grounded adversarial probes in `guard-boundary-probes.json` are
synthetic assertions, not generated model results or human annotations. Both
swapped Drug/ILThermo AULC values and “18% more queries” in place of the source's
18% saving pass current mechanical checks. Matching values/units and valid passage
IDs do not bind a quantity to its dataset, metric, comparator or direction. These
known false acceptances remain unresolved; the patch does not claim general
claim-level entailment or automated scientific validation.

Selection remains heuristic and tuned against a small convenience sample. Tables,
equations, unusual layouts, block continuations and truncated PDFs are not fully
reconstructed. Dropping dangling tails can also drop useful qualifications; the
retained document, omission labels and source checklist are needed to diagnose
that loss. An incomplete metrics list can remain explicitly labeled incomplete.
Missing selected evidence is not proof that an article omits the information.

The lexical guards can both miss paraphrased unsupported assertions and withhold
supported paraphrases. A statistical threshold does not prove a test was valid,
and an author's claim of computational success does not establish experimental or
clinical efficacy. Independent domain review remains necessary. Model sampling
and runtime variability, historical KolTa provenance gaps and the lack of a
representative human-reviewed benchmark prevent authoritative accuracy estimates.

Within the touched modules, dictionary-based records and some pre-existing long
expressions remain project conventions. There is no configured or installed
formatter/linter/type checker; syntax checks, whitespace checks, a simple AST
import-use scan and manual review are narrower checks. Future work should target
observed quantity attribution/direction failures and assess selection on held-out
articles, rather than adding more unsupported verification claims or a broad
refactoring layer.
