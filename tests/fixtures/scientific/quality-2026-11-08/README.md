# Scientific-quality evaluation archive: November 8, 2026

This small archive preserves the evidence behind
[`docs/scientific-quality-2026-11-08.md`](../../../../docs/scientific-quality-2026-11-08.md).
Scores are source-grounded agent judgments, **not human-verified scientific
accuracy**. The conclusion remains mixed, limited gains with known regressions.

- `source-checklists.json`: original rubric, essential facts, source excerpts,
  original PDF pages, passage IDs and PDF byte hashes.
- `scorecards.json`: frozen baseline judgments, their explicit erratum, final
  raw/retained judgments, rationales and known adversarial guard failures.
- `cached-cases.json`: all ten fresh raw checkpoints, including exact prompts,
  responses, generation settings, timings and completion metadata; eleven
  condition results including historical KolTa legacy; deduplicated selected
  passages; and three final retained outputs from cached revalidation. Evidence
  keys preserve passage order. The passage pool omits duplicated raw layout text,
  ranking diagnostics not needed to replay validation.
- `provenance.json`: baseline commit, source identities, recorded model digest,
  historical test results, normalized implementation hashes and preservation
  metadata. Unknown historical provenance remains unknown.
- `manifest.json`: SHA-256 of each package file after UTF-8 decoding and universal
  newline normalization, so Windows Git line-ending conversion does not invalidate
  the archive. Original checkpoint/PDF hashes refer to original bytes instead.

From the repository root, using the existing development environment:

```sh
python -m pytest tests/test_scientific_quality.py -q
```

The package tests check file integrity, prompt hashes, attempt accounting and
truncated attempts, then replay `validate_sections` against all three final raw
responses and compare retained text, issues and populated-section counts. No
Ollama server, model weights, PDFs or ignored evaluation directory are needed;
generation functions are not called. Existing project dependencies are required.

This reproduces deterministic final validation, not stochastic generation, PDF
extraction or the subjective rubric scores. Original baseline parser outcomes are
archived rather than replayed through the changed parser. In particular, Tabular
uses the earlier post-fix prompt; compact retries apply only to KolTa/CAGenMol.
Both truncated 900-token attempts and the original compact parser fallbacks remain
visible. Final retained outputs are partial, unverified summaries.

Paths inside original scorecards refer to the preserved local run; the corresponding
material needed for this review is embedded here. Complete PDFs, candidate passage
inventories, model caches and the complete ignored run are deliberately excluded.
The archive supports inspection of selected evidence and omissions; it cannot
independently reproduce every selection decision or validate table-cell extraction.
