# Q6 Final Audit — P0–P4 complete

Completed on 2026-11-20. Q6 is accepted within the evidence and limitations below. Q7 installer and release work is now WIP.

## Decision

**Go to Q7.** No reproducible Q6 blocker remains in the supported source-conversion workflow. This is not a claim of perfect conversion for every possible document.

## Delivered priority work

| Priority | Result | Evidence |
|---|---|---|
| P0 — Functional blockers | Drag-and-drop, file selection, all supported routes, parser isolation, and critical PDF value/table corruption are covered | GUI, reliability, Q6, and PDF regressions |
| P1 — Shared conversion quality | Shared output contract, metadata boundaries, validation, readable GUI profile, and safe export policies are active | Ten-format contract tests and Q6-B report |
| P2 — Format fidelity | Existing Q3/Q4 policies cover all ten formats; final PDF work maps raster images into table cells by geometry and omits empty continuation headings | Positioned-image, fallback, merged-table, and source-backed tests |
| P3 — Quality assurance | Full suite, unchanged semantic corpus, four stress cases, offline checks, and fresh-process timing/memory runs pass | 247 tests; 42 runs; 303/303 checks |
| P4 — Polish and documentation | README, roadmap, changelog, implementation status, license boundary, and release handoff are reconciled | Repository documentation audit |

## Final validation

```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider
.\.venv\Scripts\python.exe tools\evaluate_q5.py --repeat 3 --output docs\benchmarks\q6-final-windows.json
git diff --check
```

- Automated suite: **247 passed**.
- Corpus: **42/42 fresh-process runs passed**.
- Checks: **303/303 passed**.
- Formats: TXT, CSV, JSON, XML, HTML, HTM, DOCX, PPTX, XLSX, and PDF.
- Stress cases: TXT, CSV, XLSX, and PDF.
- Environment: Windows 11, Python 3.13.0.
- Measurements: [`benchmarks/q6-final-windows.json`](benchmarks/q6-final-windows.json).

The corpus uses independent generated sources and checked-in semantic expectations. It is a regression gate, not a general accuracy percentage.

## PDF closure

The PDF converter now:

- repairs structured tokens split by visual line wrapping;
- joins compatible table continuations across adjacent pages;
- keeps repeated-header tables separate;
- matches native raster images to source cells using page-space bounding boxes;
- emits HTML images inside HTML table cells;
- preserves unmatched images in an appendix instead of dropping them;
- omits headings for pages whose content was fully merged into an earlier logical table.

No filename or document-specific text participates in these rules.

## Remaining non-blocking limits

- Scanned PDFs still require an external text layer or future OCR support.
- PDF vector artwork, masks, unusual transforms, and arbitrary layouts may require full-page `pdf_mode="pages"` review.
- The Python network guard is not an operating-system sandbox or a hard RAM limit.
- An external AI or Markdown client may not decode Base64 data URIs.
- Final executable size, clean-machine behavior, Qt redistribution duties, SBOM, signing, upgrade, and uninstall behavior belong to Q7.

## License handoff

The repository MIT license covers original project work. Microsoft MarkItDown and all other dependencies retain their own licenses. `THIRD_PARTY_NOTICES.md` records the current boundaries. Q7 must generate the final inventory from the exact installer contents, including Qt/PySide6 and any native components.
