# Changelog

## Unreleased — Q4 contextual media complete (2026-11-11)

- Preserve Word/PPTX image occurrences beside their source text and captions; place Excel media by worksheet/drawing anchor and PDF visuals by page.
- Read Excel images from original archive bytes and exclude unselected worksheets' assets.
- Deduplicate repeated Markdown payloads with reference definitions; retain optional appendix placement and explicit fallback warnings.
- Extend portable ZIP export to image reference definitions and HTML image sources while preserving code examples.
- Verify PDF native JPEG byte preservation, package overwrite failure behavior and malformed Base64 rejection.
- Add sixteen Q4 acceptance cases; full suite: 150 passed. Update README and Q4 acceptance report; Q5 remains WIP.

## Unreleased — Q3 format acceptance complete (2026-11-11)

- Add page-aware PDF text, explicit two-column reading, merged-table HTML and source geometry; respect nonzero page origins.
- Preserve Word merged/nested tables, nested numbering, and two-way footnote anchors; expose parser warnings.
- Preserve PowerPoint connector IDs and chart/diagram source data alongside readable output.
- Retain XLSX numeric XML literals before float coercion and use them in numeric table cells.
- Preserve complex HTML table spans and nested code; add explicit TXT prose mode with a warning.
- Add fifteen source-backed acceptance cases. Full suite: 134 passed.
- Update README and Q3 acceptance report. Q4 and Q5 remain WIP.

## Unreleased — Q2–Q5 implementation checkpoints

- Add conversion policies, result warnings, resource budgets and atomic Markdown export.
- Preserve TXT whitespace; fence JSON/XML; retain original CSV and multiline cells; preserve XLSX string values, formulas, cache metadata, merges and worksheet selection.
- Preserve HTML preformatted text, embed allowed local images, and report unresolved assets/links.
- Add OOXML media provenance, PDF pages/images/text modes, and optional deduplicated Markdown/assets ZIP export.
- Add cooperative batch cancellation and bounded GUI preview with complete clipboard/export content.
- Add fault-injection, fidelity, privacy, resource, media and GUI regression tests; 119 tests pass.
- Add isolated ten-format timing/memory corpus and document remaining complex-format acceptance work.
- Repair README navigation with explicit anchors and correct links to installation, requirements and tests.

## Unreleased — Conversion quality audit

- Preserve converter output exactly in the embedded-media decorator, including trailing spaces, tabs, and blank lines. Add only the separator needed before the media appendix.
- Add 12 regression cases with and without embedded images; verify the complete decoded DOCX image bytes.
- Record architecture, reproducible fidelity findings, prioritized risks, quality metrics, and checkpoints Q1–Q6 in `docs/CONVERSION_QUALITY_AUDIT.md`.
- Add synthetic fidelity probes in `tools/audit_conversion_quality.py`.
- Update README status and limitations. Q1 is complete; Q2 is WIP. Release packaging follows quality hardening.
- Validation: 80 tests passed before the change; 92 passed afterwards. Upstream whitespace normalization and the documented XLSX/CSV issues remain unresolved.
