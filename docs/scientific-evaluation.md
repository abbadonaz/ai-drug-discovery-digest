# Scientific summary evaluation (A03)

This benchmark evaluates summaries of computational **small-molecule** drug discovery studies. It is an offline evaluation tool, not a change to evidence extraction, summarization, prompts or claim verification. The existing `evaluation.harness.run_evaluation()` and `digest-evaluate` formatting/relevance checks remain unchanged. Their recall and formatting pass rates do not establish scientific quality.

## Starter dataset and scientific scope

`tests/fixtures/scientific/benchmark.json` contains **seven synthetic cases**, one each for QSAR/ADMET, graph representations, uncertainty, active learning, generative multi-objective design, docking/molecular dynamics, and foundation-model transfer. Every title, dataset, result and number is invented explicitly for testing. The passages are toy study descriptions, not excerpts from real publications. The annotator is recorded as the synthetic fixture author; none is represented as human-reviewed science.

There are **zero verified real-paper cases and zero unreviewed real-paper candidates** in this release. Therefore there is no authoritative real-paper scientific-quality baseline yet. Do not use the synthetic agreement rate as a measure of production summary accuracy. The accurate fixture copies the reference statements intentionally to test evaluator behavior; it is not pipeline-generated output. The negative fixture contains 23 deliberately incorrect statements across seven cases.

The starter exercises improvements limited to particular datasets or splits, internal versus external validation, regression versus classification metrics, uncertainty versus calibration, prediction versus measurement, docking versus binding, generated versus synthesized molecules, dataset bias and generalizability. Grow toward 15–25 real cases through review, not by relabeling synthetic examples or generating purported human annotations.

## Schema and versioning

`evaluation.scientific_schema` defines strict Pydantic models using the existing dependency. `tests/fixtures/scientific/benchmark.schema.json` is the generated JSON Schema for editor validation. Unknown fields and schema versions are rejected. The JSON root has `schema_version` (currently `1.0`), `benchmark_version`, and `cases`. Increment the benchmark version whenever annotations change; use a new schema version for incompatible structural changes.

Each case includes:

| Field | Meaning |
| --- | --- |
| `id`, `title`, `identifier`, `url` | Stable case ID, title, optional DOI/arXiv identifier and exact pipeline URL |
| `kind` | `synthetic` or `real` |
| `domain` | `qsar_admet`, `representations_gnn`, `uncertainty`, `active_learning`, `generative_design`, `structure_based`, `foundation_models` |
| `source_ref`, `source_sha256` | Local document/fixture reference and immutable source-byte hash; required hash for verified real cases |
| `evidence_scope` | `abstract_only`, `full_text`, or `unknown`; scope of the reference annotations |
| `passages` | ID, verbatim source text, section and optional one-based PDF page |
| `annotations` | ID, category, complete qualified statement, evidence IDs, optional manually checked full-sentence variants |
| `quantities` | Annotation ID, value, unit, metric, dataset, direction, conditions and baseline; use `dimensionless` where appropriate |
| `must_not_infer` | Explicit false/unsupported statements, error type, reference evidence, rationale, and optional related annotation ID |
| `reference_summary` | Optional reference text; not required and never generated automatically |
| `review` | Status, annotator, reviewer/date when verified, and provenance/review notes |

Annotation categories are `finding`, `method`, `result`, `comparison`, `limitation`. IDs and evidence references are validated. Missing annotation categories have null metric values, not perfect scores. A real candidate uses `review.status=unreviewed`. Verified real cases require `status=verified`, reviewer/date, source hash, evidence passages and annotations. Synthetic cases must use `status=synthetic` and cannot enter the verified cohort.

These checks validate metadata consistency, **not reviewer identity or scientific correctness**. Approval is a human responsibility enforced through repository review. A SHA-256 hash records provenance; it does not certify a source or reviewer. The evaluator never fetches documents or validates citations online.

### Synthetic annotation example

The complete example is `synthetic-qsar` in the dataset. Its invented source states: “On SolToy scaffold test data, RMSE decreased from 1.2 to 1.0 log mol/L relative to a random forest.” The `result` annotation links this exact statement to `E1`; the quantity records `1.0`, `log mol/L`, `RMSE`, `SolToy`, the scaffold test condition and random-forest comparator. Separate annotations record that the advantage did not hold on LipToy and no external validation was performed. Explicit negative controls change the value, unit, metric, dataset, direction or split, and assert universal superiority or external validation. All these numbers describe a fictional toy study only.

## Automated checks versus scientific judgments

The evaluator has no model dependency, no retrieval, no Ollama calls and no embedding computations. It reads supplied JSON and prints a report; it does not write production data.

| Output | Interpretation and denominator |
| --- | --- |
| `coverage_proxy` | Number of annotated statements matched / number of annotated statements, by category and overall (micro-average). Exact full sentences are compared after whitespace/case/final punctuation normalization. This is lexical coverage, not semantic finding coverage. Unmatched annotations may be omissions **or valid paraphrases**. |
| `quantitative_checks` | `reference_match` only when the entire annotated qualified quantitative statement matches; `failed` on an explicit linked quantitative negative control; otherwise `not_assessed`. Values alone cannot pass. |
| `quantitative_reference_agreement` | Reference matches / (reference matches + explicit failures). Unassessed quantities are excluded and their count is shown alongside; do not compare this ratio without its denominator. |
| `negative_controls` | Exact full-sentence violations produce `failed` with error type, reference and rationale. No match produces `no_known_violation`, never “scientifically correct.” |
| `evidence_support` | Per-claim `supported`, `contradicted`, `insufficient_evidence`, or `not_assessed`. **Only separate human assessments populate the first three.** Incoming positional provenance, scores and even a supplied `support_status=supported` are ignored. |
| `human_supported_fraction` | Human-supported claims / human-assessed claims. Unassessed claims excluded and counted. This is reviewer judgment, not objective or automated verification. |
| `human_assessment.rubric` | Optional ordinal human ratings; never inferred, summed into an overall score or pooled with automated metrics. |

Negative-control reference labels (`contradicted` or `insufficient_evidence`) describe the annotation author's rationale. They are not silently promoted to an independent human judgment on the candidate summary. Explicit rules fail for known value/unit/metric/dataset/direction/condition errors, external-validation claims, experimental-confirmation claims, significance, superiority, unsupported results and lost qualifications. The rule library is deliberately finite: an unfamiliar numeric claim is unassessed, not automatically a hallucination. Human reviewers must evaluate the rest.

Sentence segmentation is a lightweight punctuation/newline heuristic; abbreviations, lists, complex prose and multi-claim sentences can require review. Case folding and punctuation normalization can also obscure distinctions in specialized notation. It is not a semantic parser. Accepted variants must retain every essential qualification. Positive substring matching is intentionally avoided so negated or extended statements do not inherit a positive match.

Lexical similarity, ROUGE and embedding similarity alone cannot establish factuality: an incorrect unit, negation, split or experimental qualifier may leave nearly all words or embeddings unchanged. Conversely, an accurate paraphrase may have little lexical overlap. Exact statement checks here are reproducible regression controls, not a substitute for reading evidence.

## Running and comparing evaluations

From the repository root using the installed project environment:

```powershell
python -m evaluation.scientific --benchmark tests/fixtures/scientific/benchmark.json --summaries tests/fixtures/scientific/summaries-accurate.json --timestamp 2026-11-07T00:00:00Z
python -m evaluation.scientific --benchmark tests/fixtures/scientific/benchmark.json --summaries tests/fixtures/scientific/summaries-negative.json --timestamp 2026-11-07T00:00:00Z
python -m evaluation.scientific --benchmark path/to/reviewed-benchmark.json --summaries data/summaries.json
```

The input is an ordinary pipeline `summaries.json` array: `tldr`, `url`, optional `generation_mode` and `evidence_mode`. An optional `case_id` takes precedence over URL matching. Without it, matching uses exact URL; titles are never fuzzy-matched. Duplicate matches fail rather than choosing silently. Unmatched outputs are counted, absent summaries are reported, and missing modes remain `unknown`. Empty summaries count as supplied/evaluated with zero available coverage and a `summary_text` missing flag; absent summaries do not enter coverage denominators. Brief references therefore cannot appear to have perfect coverage.

Generation and evidence modes are propagated, not inferred. Reference evidence scope and the pipeline's evidence mode are separate: full-text preparation does not prove the summarizer actually used full text. `fixture` generation mode labels the synthetic test outputs only and is not a new production mode.

Reports include evaluator/schema/benchmark versions, timestamp, canonical JSON hashes for benchmark/summaries/assessments, case counts, per-case results, all three separate cohort aggregates, missing fields and unassessed claims. No overall quality score is calculated. Use `--timestamp` to fix the report timestamp for byte-stable comparison; default timestamps record current UTC.

To compare two pipeline versions, save their outputs outside production paths, use the **same benchmark revision and evaluator version**, and evaluate each. Compare category coverage, explicit failures, quantity assessment counts, evidence modes and missingness on the same matched cases. Preserve report/input hashes and record pipeline commit/model/configuration separately. Do not compare aggregate ratios from different case sets as though they measured an improvement. This framework accepts future extraction/selection/verification outputs without changing the production pipeline.

## Adding and reviewing real papers

1. Select a computational small-molecule study and retain a legal local source snapshot. Record title, DOI/arXiv version, exact pipeline URL, source reference and SHA-256 of the original bytes. Use a new stable ID and `kind=real`, `review.status=unreviewed`.
2. Read the source, not just the generated summary. Transcribe short evidence passages exactly with section/page. Record abstract-only scope if full text is unavailable. Keep original metric definitions, units, uncertainty intervals, dataset identity, splitting procedure and conditions. Do not infer missing results from plots without documenting the extraction method.
3. Annotate main findings, methodological requirements, quantities, comparators and limitations. Separate computational predictions from assays, internal from external validation, confidence from calibration, and statistical significance from numerical differences. Record known unsupported inferences with precise rationales; absence of a reported experiment is not proof that a scientific hypothesis is false.
4. Have a human domain reviewer independently check every passage, annotation, accepted variant and negative control against the saved source. Resolve disagreements in review notes. Only then set `status=verified`, reviewer identity and review date through a reviewed commit. The tool cannot perform this approval. A second independent reviewer and adjudication are recommended for authoritative comparisons.
5. Bump the benchmark version and validate through `Benchmark.model_validate_json(...)` or an evaluation run. Add an accurate output and meaningful negative controls, test them, and inspect denominators. Keep unreviewed annotations outside authoritative aggregates.

## Human summary assessment and usefulness rubric

Optional `--assessments path/to/assessments.json` accepts an array of `HumanAssessment` records. Each includes `case_id`, `benchmark_sha256` from the report, `summary_sha256` for the exact UTF-8 `tldr`, `reviewer`, `reviewed_at`, optional `claims`, and optional `rubric`. Benchmark and summary hashes must match before judgments are used. Claim text must correspond to a segmented summary claim. Supported/contradicted judgments require valid reference evidence IDs; every judgment requires a rationale. Changed summaries or benchmark annotations require renewed review.

For each claim, choose supported only if the evidence warrants the full claim including qualifiers; contradicted if the source conflicts; insufficient evidence if the provided source cannot establish it; otherwise not assessed. Review unassessed claims explicitly. Optional rubric dimensions are `accuracy`, `methodology`, `quantitative_information`, `coverage`, `limitations`, `drug_discovery_relevance`. Omit dimensions that cannot be judged; do not use zero for missing data.

| Dimension | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| Accuracy | Central claim contradicted (e.g. docking called binding proof) | Material unsupported assertion | Accurate essentials with minor imprecision | All reviewed claims preserve evidence and qualifications |
| Methodology | Wrong method/validation design | Generic “AI model” only | Method and validation mostly clear | Method, comparator and relevant split/conditions explicit |
| Quantitative information | Incorrect/misleading result | Key available result omitted | Correct main result with partial context | Values, units, metric, dataset, comparator and conditions clear |
| Coverage | Main contribution missing | Only peripheral findings | Main finding plus some essential context | All essential findings and qualifications covered |
| Limitations | Reverses/denies a central limitation | Omits material limitations | Main caveat conveyed | Relevant applicability and uncertainty limits clearly preserved |
| Drug-discovery relevance | Misrepresents the application | Vague relevance | Specific computational application | Clearly explains the demonstrated utility without translational overclaim |

These are subjective ordinal judgments, not interval measurements. Record disagreements; do not average them into a purported objective quality score. Quantitative informativeness is unassessable when the reference contains no quantitative result. Reviewer identities, timestamps and notes are records, not cryptographic authentication.

## Remaining gaps before A15

The principal gap is a human-reviewed real-paper corpus with representative tasks, unsuccessful results, chemical domains and evidence quality. Seven synthetic templates favor exact wording and cannot estimate error rates on production summaries. There is no automatic entailment model, generalized numerical relation extraction, statistical significance verification or verified claim-generation mechanism. Selection bias, reviewer disagreement, missing full text, version drift and incomplete annotations can dominate reported scores. Evaluate future extraction changes against reviewed sources and frozen outputs; this PR does not implement those changes.

## Measured fixture baseline

`docs/scientific-evaluation-baseline.json` records versioned input hashes, cohort denominators and per-case results for both fixture sets, using a fixed timestamp for reproducibility. The accurate fixture matches 35/35 reference statements and 3/3 complete quantitative statements. The negative fixture triggers all 23 annotated controls across seven cases and fails all three quantitative records. All 35 accurate-fixture claims and 23 negative-fixture claims retain `not_assessed` evidence support in the absence of a human assessment. The verified cohort has zero cases and null rates.

Reading the existing production `data/summaries.json` found 22 readable outputs, none matching this synthetic benchmark. It produced zero evaluated cases and null scores rather than invented annotations. Neither run modifies its input. The focused command `python -m pytest -q tests/test_scientific_evaluation.py tests/test_evaluation_harness.py` passed 49 tests, including network-blocked deterministic execution, the unchanged legacy harness, every negative control, missing annotations/modes, cohort separation, stale assessment rejection, and a subprocess CLI run without loading Torch/Ollama/embedding libraries.

The complete regression suite, `python -m pytest -q`, passed **316 tests**. Existing production modules, summaries, digests, caches and untracked audit artifacts were left unchanged.
