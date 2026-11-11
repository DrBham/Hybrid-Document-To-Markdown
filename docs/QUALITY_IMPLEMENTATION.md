# Q2–Q5 implementation and validation

This report supplements the historical Q1 audit. Implemented behavior below is verified against synthetic fixtures. Complex-document acceptance remains open where explicitly listed; the complete Q2–Q5 programme must not be declared finished from smoke tests alone.

Update 2026-11-11: Q3 acceptance is complete with **134 passing tests**. [Q3_ACCEPTANCE.md](Q3_ACCEPTANCE.md) supersedes the earlier Q3 pending items and documents policies/limits. The timing/memory table below remains a historical baseline of the previous implementation, not a benchmark of the new PDF/Office paths.

Q4 update: **150 tests pass** after source-context placement, deduplication and portable asset export acceptance. [Q4_ACCEPTANCE.md](Q4_ACCEPTANCE.md) defines the completed scope and limitations. Q5 remains WIP.

## Delivered checkpoints

| Area | Delivered | Validation |
|---|---|---|
| Q2 | Backward-compatible result warnings, conversion options, atomic Markdown publication, ZIP/input/output/page/pixel/cell budgets, resource cleanup, shared fences and table escaping | Original suite plus replace failure, competing publisher, archive/output/page/pixel rejection |
| Q3 | Exact decoded TXT, fenced JSON/XML, CSV dialect selection with original source, cell-based XLSX/formula/cache metadata and sheet selection, HTML pre blocks/local assets | Exact text, numeric strings, formula, merge metadata, namespaces/CDATA, multiline cells, image round-trip |
| Q3 completed | Word semantic tables/lists/notes, PDF columns/geometric tables, PowerPoint connector/chart source records, literal XLSX numeric XML | Fifteen source-backed acceptance cases; see Q3 report |
| Q4 | Base64 default; optional ZIP with relative assets and hash deduplication; OOXML relationship provenance; PDF pages/images/text modes | Byte comparisons, ZIP references/deduplication, three PDF modes |
| Q5 | Cooperative cancellation between files; bounded preview with full copy/export; warnings in GUI; isolated ten-format corpus with time and process memory | Offscreen GUI, cancellation/restart, network-blocked HTML fixture, resource/failure tests, corpus runner |

New modules: `core/options.py`, `core/serialization.py`, `converters/faithful_converter.py`, `converters/local_html_converter.py`, `services/asset_package.py`. Existing router, result model, media extraction, exporter, batch service and GUI integrate these changes. Tests are in `tests/test_quality_hardening.py` and `tests/test_gui.py`.

## API and compatibility

```python
from pathlib import Path
from document_converter.core.options import ConversionOptions
from document_converter.core.router import ConverterRouter
from document_converter.services.asset_package import AssetPackageExporter

options = ConversionOptions(
    encoding="utf-8-sig",       # Explicit strict decoding; cp1252/utf-16 can be selected.
    text_mode="preserve",       # Optional prose mode explicitly normalizes whitespace.
    csv_delimiter=None,          # Infer comma/semicolon/tab/pipe; specify when ambiguous.
    pdf_mode="pages",            # pages (default), images, or text
    pdf_columns=1,               # 2 for equal-width two-column pages; explicit, not inferred.
    media_placement="context",  # Default source placement; "appendix" is also available.
    spreadsheet_view="formula", # formula or cached; metadata retains formula either way
    sheets=(),                  # All sheets, or a tuple of worksheet names
)
result = ConverterRouter(options=options).convert(Path("report.xlsx"))
print(result.warnings)
AssetPackageExporter().export(result.markdown, Path("report.zip"))
```

The GUI retains single-file Base64 Markdown by default. Advanced conversion options and ZIP export are currently core API features. ZIP contains `document.md` plus `assets/`; extract both together. Identical byte payloads of the same MIME type share one asset. A ZIP is an optional packaging format, not a change to `.md` syntax.

Output changes are intentional: JSON/XML gain fences; CSV gains a raw-source appendix; XLSX includes cell metadata. TXT preserves decoded line endings/whitespace. Strict decoding raises an error instead of discarding bytes. Fences may introduce the terminal newline needed by Markdown; they are not a byte-perfect container of the original file encoding/BOM.

Default limits: input 100 MiB, archive 10,000 entries / 256 MiB expanded, output 128 MiB UTF-8, PDF 500 pages / 20 million pixels per page or extracted image, workbook/CSV 250,000 cells. Limits fail explicitly; no silent truncation. These are configurable safeguards, not a hard process RAM or execution-time sandbox. Third-party parsers still allocate memory before some post-conversion checks.

Atomic Markdown publication writes and syncs a sibling temporary file, then replaces the destination for authorized overwrite or publishes an exclusive hard link. Filesystems without hard-link support fail safely instead of falling back to partial writes. Temporary files are cleaned on failure. No claim of power-loss durability for the directory entry is made.

Cancellation finishes the current file and marks remaining files cancelled. It cannot interrupt an executing third-party parser. Preview shows at most 200,000 characters; Copy and Save retain the full result. Warnings are visible in file status/tooltips and preview summary.

## Before / after

| Case | Before | After |
|---|---|---|
| TXT trailing spaces and blank lines | Removed by upstream normalization | Exact decoded source string |
| XLSX string `00123` | `123` | `00123` |
| XLSX string `9007199254740993` | `9.007199e+15` | `9007199254740993` |
| XLSX `=1+2`, no cache | `NaN` | Formula retained; cached view says cache unavailable; warning |
| CSV semicolon | Single column | Detected columns, with explicit delimiter override |
| CSV multiline cell | Newline replaced by space | `<br>` in table and original source in fenced appendix |
| HTML preformatted source | Trailing spaces/blank lines changed | Preserved in a safe fence |
| Local HTML image | Unpackaged relative reference | Base64 when inside source directory and within budget |
| Failed overwrite | Could truncate original file | Original retained if replacement fails |

## Executed validation

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe tools\audit_conversion_quality.py
.\.venv\Scripts\python.exe tools\evaluate_quality.py
git diff --check
```

Historical Q2–Q5 checkpoint: **119 passed in 9.06s**, Windows / Python 3.13.0. Corpus checks passed for all ten extensions in separate subprocesses. Current Q3 closure: **134 passed in 77.25s** (2026-11-11). Neither is a measured general-purpose accuracy percentage.

One-run synthetic baseline (conversion elapsed time excludes router construction; peak memory includes imports, fixture generation and native allocations):

| Format | Seconds | Process peak bytes | Output bytes |
|---|---:|---:|---:|
| TXT | 0.014110 | 145620992 | 16 |
| CSV | 0.012322 | 145928192 | 112 |
| JSON | 0.010571 | 145346560 | 43 |
| XML | 0.011410 | 145686528 | 53 |
| HTML | 0.011442 | 146169856 | 35 |
| HTM | 0.015602 | 145801216 | 18 |
| DOCX | 0.172374 | 167350272 | 15 |
| PPTX | 0.029019 | 147316736 | 32 |
| XLSX | 0.020275 | 145797120 | 615 |
| PDF | 0.061224 | 148381696 | 449 |

Each corpus result records its actual checks, source/output size, timing, warnings and memory. Corpus size is one small fixture per format; it does not establish p95 performance or behavior of large real documents. Regression tests provide more detailed oracles than this smoke corpus.

## Remaining acceptance work

- Q3 closed: tests now cover explicit PDF columns/merged tables, Word lists/footnotes/complex tables, PowerPoint chart/connector metadata, and XLSX numeric XML literals. The Q3 report records limits; arbitrary-layout perfection is not claimed.
- Q4 closed: Word/PPTX source positions, Excel worksheet anchors and PDF page placement are tested alongside Base64/ZIP deduplication. Unknown positions use an appendix with warnings. PDF masks/vector artwork and inferred caption relationships remain limitations, as detailed in the Q4 report. No OCR or content interpretation is added.
- Q5: large-document stress tests, a reviewed golden corpus of complex layouts, cancellation within a file, process timeouts and offline interception across every parser remain pending. Network blocking was tested on the local HTML path only. No fuzzing or complete security audit is claimed.
- Exported relative hyperlinks can require external companion documents. ZIP export repackages supported Base64 image references only; it does not crawl links or fetch network resources.
- Profiles are deferred until these source fidelity contracts stabilize. No additional parser dependency was introduced.

Next checkpoint: Q5 stress/corpus/quality gates before Q6 release work.
