# Changelog

## Unreleased — Q6-C DOCX P1 fidelity (2026-11-22)

- Map Word structure to Markdown headings when built-in Heading styles are absent: outline levels, Title, bold numeric labels (`2.1.` becomes a level-3 heading), and short bold uppercase section names.
- Keep whitespace-only formatted runs so adjacent words such as `Contoh Gambar` stay separated.
- Honor direct `w:b w:val="0"` over bold character styles such as Strong.
- Replace empty or noise image alt text with the nearest caption (caption style, SEQ field, or label-number pattern).
- Add five DOCX regressions, including two-column reading order and byte-identical full-resolution image round-trip; the suite passes 258 tests and the Q5 corpus gate still passes.

## Unreleased — Q6-C DOCX P0 fidelity (2026-11-22)

- Convert Word OMML equations to inline `$...$` or display `$$...$$` LaTeX, filling OMML default properties the bundled converter requires; unconvertible equations keep their plain text with a warning.
- Use the first row of simple Word tables as the Markdown header instead of an empty generated header row.
- Compute list labels from `numbering.xml` in document order, including custom level text, letter/roman formats, start overrides, style-linked numbering, and nested bullets.
- Add six DOCX regressions; the suite passes 253 tests and the Q5 corpus gate still passes 42 fresh-process runs.

## Unreleased — Q6 P2–P4 complete (2026-11-20)

- Map extracted PDF raster images to source table cells with generic page-space bounding boxes; preserve unmatched images in the appendix with a warning.
- Remove empty PDF page headings created when table continuations merge into an earlier logical table.
- Keep prior PDF structured-value and cross-page table repairs intact without document-specific filenames or content rules.
- Pass 247 automated tests plus 42 fresh-process corpus runs and 303/303 checks across ten formats and four stress cases.
- Record the Q6 go decision, benchmark evidence, remaining limits, and Q7 installer handoff.

## Unreleased — Q6 PDF P1 user-facing output profile (2026-11-19)

- Make GUI PDF conversion embed source image objects instead of full-page screenshots.
- Omit diagnostic geometry appendices from GUI exports while retaining readable tables and Base64 image data.
- Keep the API fidelity profile unchanged; callers can still request rendered pages and embedded source metadata.

## Unreleased — Q6 PDF P0 quality fixes (2026-11-19)

- Repair structured values split by visual line wrapping inside PDF table cells, including numeric fragments and punctuation-delimited JSON fields.
- Join compatible table segments that continue across adjacent PDF pages while keeping repeated-header tables separate.
- Preserve original extracted rows in embedded geometry metadata whenever a repair changes visible cell text.
- Add regressions for token repair, cross-page row continuation, repeated headers, and existing merged/multiline table behavior.

## Unreleased — Q6-B shared output policy and all-format audit (2026-11-17)

- Add a router-level output contract for source identity, format identity, UTF-8 safety, NUL rejection, unresolved-placeholder rejection, warning canonicalization, and final output limits.
- Add explicit structured-metadata boundaries for XLSX cell records, PDF table geometry, and PPTX source structure while preserving fidelity-first Markdown by default.
- Add `metadata_mode="omit"` for consumers that want readable content without diagnostic source appendices.
- Add twenty Q6-B regression cases, including a direct gate for TXT, CSV, JSON, XML, HTML, HTM, DOCX, PPTX, XLSX, and PDF.
- Validation: **242 tests pass**; the unchanged source-authored corpus passes **101/101 checks** across ten formats and four stress cases. See `docs/Q6_CHECKPOINT_2.md`.

## Unreleased — Q6 drag-and-drop P0 fixed (2026-11-17)

- Detect the extension of files dropped from local URL payloads instead of applying the initial TXT Browse filter.
- Accept drag-enter and drag-move only when at least one existing local file uses a supported extension; decode Windows file URLs through Qt.
- Keep same-extension batch policy, reject mixed supported formats atomically, skip unsupported files with feedback, and preserve the existing Browse filter workflow.
- Clarify the GUI helper text: the selector filters Browse while drag-and-drop detects the file type automatically.
- Follow up on the supplied Windows recording: make the complete Add documents card—including its labels, selector, and button—the sole document drop target.
- Add seventeen Q6 GUI cases covering all ten extensions, uppercase names, spaces, Unicode, multiple files, unsupported payloads, mixed formats, visual drag state, Add documents child routing, and Browse regression.
- Validation: 29 focused GUI tests and the complete **222-test** suite pass. Native Explorer automation could not run because the Codex Windows UI helper failed to initialize; a manual recheck is documented.

## Unreleased — Q5 reliability and evaluation complete (2026-11-11)

- Run built-in batch conversions in disposable parser processes with active cancellation, a configurable 120-second per-file deadline, private scratch cleanup and independent failure outcomes.
- Block Python socket networking in workers and avoid exposing parser exception contents in user-facing diagnostics.
- Load parsers on demand so text conversion does not require Office/PDF dependencies.
- Read Excel formula caches in one pass instead of repeatedly reparsing worksheet XML. The 5,000-formula fixture previously timed out at 120 seconds; the new three-run median is 0.503206 seconds on the recorded machine.
- Add source-authored semantic goldens for ten extensions, four bounded stress cases and a benchmark runner that fails on broken gates.
- Add 55 regression cases, including actual worker results, cancellation, crashes, missing dependencies, empty/malformed documents and GUI heartbeat checks. Full suite: 205 passed in 40.50s.
- Record 42 passing evaluation runs with timing/memory methodology; update README and roadmap for stabilization before packaging. No new dependency or model is added.

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
