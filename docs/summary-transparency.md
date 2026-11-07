# Summary provenance and mode metadata

These additive fields describe execution and evidence availability, not scientific validity.

| Location | Field | Allowed values |
| --- | --- | --- |
| Each newly generated provenance claim | `support_status` | `unverified` |
| Summary record | `generation_mode` | `llm`, `extractive_fallback`, `unavailable`, `not_generated`, `unknown` |
| Prepared evidence and summary record | `evidence_mode` | `pdf_full_text`, `abstract_only`, `unknown` |

`llm` means an LLM result passed the existing presentation checks, including when an optional QA warning is appended. It does not mean factual support was established. `extractive_fallback` identifies the extraction execution path, including its existing brief-evidence notice. `unavailable` identifies a failure placeholder without an extracted summary. Brief references are `not_generated`. Missing legacy metadata defaults to `unknown`; modes are never inferred from prose.

`pdf_full_text` means non-abstract PDF sections were retained during evidence preparation. The summary selector may still choose only abstract passages, so the HTML explicitly says full text is available rather than asserting it was cited. `abstract_only` describes an abstract fallback or a prepared PDF record retaining only an abstract. A download or PDF URL alone never establishes full-text evidence. When PDF evidence fails validation and preparation falls back to the source abstract, the mode becomes `abstract_only`.

Claim/snippet structures and existing selection roles/scores remain unchanged for compatibility. A historical role named `supporting` is a selection category, not a support verdict; it is not presented as support in HTML. All candidate associations are unverified, including legacy entries without status and imported entries asserting verification: no verification mechanism exists in this pipeline. The UI labels them **Candidate source passages**, preserves escaped claims/snippets, and states that factual support has not been verified. No entailment model or support score is introduced.

The string-returning `summarize_paper()` and `_extractive_fallback_summary()` interfaces remain available; structured outcomes carry modes internally. Evidence preparation, normal summarization, both per-paper fallback levels, orchestration failure placeholders, ranking and JSON/publication preserve the fields. Brief records have no prepared evidence and therefore use `unknown`. Existing saved JSON requires no migration and is not rewritten by this change.

This scope does not change prompts, retrieval, clustering, scoring, optional QA behavior, or the weekly narrative. Narrative fallback honesty, factual verification, page/span provenance and durable model/prompt identity remain separate work. The existing two-claim/two-passage display limit is unchanged.
