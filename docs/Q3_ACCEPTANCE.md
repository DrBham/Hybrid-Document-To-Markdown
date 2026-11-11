# Q3 — Format fidelity acceptance

Q3 implements the format-specific policies below. Acceptance is based on reproducible source fixtures, not a claim that every possible Office/PDF layout is lossless. Q4 asset/caption placement and Q5 broader corpus/stress evaluation remain separate.

## Delivered checkpoints

| Checkpoint | Implementation | Acceptance evidence |
|---|---|---|
| TXT / JSON / XML | Exact decoded TXT by default, explicit prose mode, safe source fences without parse/re-serialization | Unicode, whitespace, empty text, literal numbers, backticks, XML entity text without external resolution |
| CSV | String fields, bounded dialect inference/override, multiline presentation and original source appendix | Leading zeros, pipes, semicolon, quoted newlines and source recovery |
| XLSX | Formula/cache/cell metadata, sheet selection, merged ranges and literal XML values before Python float coercion | Numeric XML `1.2300`, `9007199254740993`, `0.123456789012345678901` retained in tables and `xml_value` |
| DOCX | Mammoth semantic extraction, protected complex tables and note anchors, parser warnings | Nested numbering with continuation, merged/nested tables, document order, two-way footnote links |
| PPTX | Existing readable conversion plus actual shape IDs, connector endpoints, chart/SmartArt data XML | Real chart values, connector start/end IDs, existing slide/table/notes tests |
| HTML/HTM | Protected preformatted blocks and semantic complex tables, local assets and link policy | Merged spans, code inside tables, pre whitespace, image byte preservation, outside-root rejection |
| PDF | Page-aware text, explicit column count, ruled-table geometry and semantic cell spans | Equal-width two-column reading, merged header, multiline table cells, nonzero page origin |

## Files and mechanism

- `converters/layout_pdf.py` extracts text in page/column order and keeps detected table geometry. HTML spans express merged cells; a JSON appendix preserves rectangles and row values.
- `converters/semantic_office.py` retains Word structures that flat Markdown cannot represent. Protected note anchors survive both the forward and return links.
- `converters/office_structure.py` reads literal worksheet XML values and actual PowerPoint shape/connection records. Diagram relationships are taken from source IDs, never inferred from proximity.
- `converters/faithful_converter.py`, `converters/local_html_converter.py`, `core/options.py`, and `core/router.py` integrate these paths.
- `tests/test_q3_acceptance.py` generates source documents with known content, numbering definitions, relationships and PDF coordinates. No private document is needed.

No new dependency was installed. Existing GUI/export/Base64 contracts remain covered by regression tests.

## Options and limits

```python
from pathlib import Path
from document_converter.core.options import ConversionOptions
from document_converter.core.router import ConverterRouter

# Explicit equal-width, two-column PDF reading; default is one column.
result = ConverterRouter(options=ConversionOptions(
    pdf_columns=2,
    pdf_mode="pages",
)).convert(Path("report.pdf"))

# Optional prose normalization; preserve is the default for TXT.
result = ConverterRouter(options=ConversionOptions(
    text_mode="prose",
)).convert(Path("notes.txt"))
```

- PDF columns are explicitly selected through the core API. Mixed-width columns, spanning titles and irregular magazine layouts still require review. Line breaks are retained rather than guessing sentence joins or semantic headings from font size.
- PDF table extraction targets detectable geometric/ruled tables. Borderless or irregular tables may remain text. Table geometry is preserved for source comparison. Textless pages produce a warning; no OCR was added.
- Word and HTML merged/nested tables and Word notes use semantic HTML inside Markdown. Viewer support varies. Parser warnings disclose unsupported Word constructs; this is not a full recovery of every Word feature.
- PowerPoint source metadata preserves connector endpoints and chart/diagram XML. It does not narrate a diagram or reconstruct missing arrows. Image placement remains Q4 work.
- XLSX `xml_value` is the authoritative literal from the saved source. `value` remains the parsed Python representation and may differ. Numeric table cells use the XML literal. Precision already lost before the workbook was saved cannot be recovered. Dates retain ISO presentation alongside XML value and number format metadata.
- Prose mode changes whitespace and emits a warning; preserve mode retains decoded source text. Encoding is explicit and strict. Fenced source is not a byte-identical container of the original encoding/BOM.

## Validation and before/after

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_q3_acceptance.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
git diff --check
```

Final validation on 2026-11-11: **134 passed in 77.25s** on the Windows development environment. Fifteen Q3 acceptance cases augment the previous 119 tests. Existing GUI, export, Base64, resource budgets and all-format tests still pass. This duration is a single full-suite run, not a conversion performance benchmark. `git diff --check` and README navigation targets are checked separately during handoff.

| Before | After |
|---|---|
| Side-by-side PDF lines could interleave under a one-column policy | Explicit two-column mode reads the entire left column before the right |
| Merged table relationships could flatten away | Semantic HTML preserves spans and nesting; PDF also retains geometry |
| Footnote return-link ID disappeared during Markdown conversion | Both the reference anchor and note-body anchor remain |
| Python float coercion could round XLSX numeric source literals | Original XML literal is separately preserved and used in numeric cells |
| Diagram connection IDs were absent from Markdown | Source-structure appendix records actual connector endpoints |
| A preformatted block inside a protected HTML table could leave a placeholder | Code remains a semantic `<pre>` inside its table |
| PDF crop assumed a zero page origin | Crops now use the actual page bounding box |

The nested-list fixture explicitly declares its second OOXML numbering level. An undeclared level is not valid evidence of a parser defect. Tests check concrete relationships and values, not only output length.

After Q3 acceptance, the next work is Q4 contextual asset/caption placement and Q5 broader corpus/stress validation. Neither phase is claimed complete here.
