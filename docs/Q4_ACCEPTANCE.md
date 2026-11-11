# Q4 — Contextual media and portable assets

Completed on 2026-11-11 for the placement and packaging policies below. The full suite passes **150 tests**, including **16 new Q4 acceptance cases**. Q5 broader stress/corpus evaluation remains WIP.

## Delivered checkpoints

| Checkpoint | Implementation | Acceptance evidence |
|---|---|---|
| Q4A — Source context | Word image occurrences follow the semantic document stream; PowerPoint uses native shape ordering; Excel resolves drawing relationships and cell anchors; PDF images belong to their page | Word/PPTX captions remain after the intended image; repeated occurrences retain order; XLSX D5 anchor; PDF page 1/2 separation |
| Q4B — Portable assets | Base64 default; reference definitions share repeated payloads; ZIP rewrites supported inline Markdown, reference definitions, and HTML image sources into `assets/` | Repeated images share one payload/file; all generated package references resolve; decoded bytes match source; HTML table images export correctly |
| Q4C — PDF visual modes | Existing `pages`, `images`, and `text` modes now respect page placement | Three-mode tests; native PDF JPEG stream is byte-identical after extraction; text mode has no visual payload |
| Q4D — Policy evaluation | Explicit options retained instead of ambiguous presets; OCR remains outside scope | `media_placement` selects context or appendix; no cloud/model dependency introduced |

## User-visible behavior

- Word: an image stays at its document position. Nearby caption paragraphs remain in their original order. A caption is not invented, rewritten, or inferred from an unrelated paragraph.
- PowerPoint: each image stays within its slide and native geometric shape traversal. Existing caption text remains in that traversal. This preserves source order, not an inferred reading order for arbitrary diagrams.
- Excel: images appear inside their worksheet section with the actual drawing start cell (or an explicit absolute-anchor label). They are not inserted into a fabricated table cell. Original image bytes come from the OOXML archive. Selected-sheet conversion excludes images from other sheets, even when the chosen sheet contains no images.
- PDF: page images or extracted images appear after the corresponding page's text. Captions remain in page text; there is no claimed one-to-one geometric caption matching. `pages` preserves raster page appearance; `images` can omit vector artwork/masks; `text` intentionally excludes visuals.
- Images without a verified placement are preserved in the appendix with a warning. Unsupported image MIME types produce a visible placeholder and warning. Some source formats/encodings remain unsupported; no universal visual completeness is claimed.

Repeated Markdown images use ordinary reference syntax:

```markdown
![First occurrence][hybrid-media-content-hash]
![Second occurrence][hybrid-media-content-hash]

[hybrid-media-content-hash]: data:image/png;base64,...
```

The reference definition remains in the same `.md` file. Both image positions share one Base64 payload. Images inside semantic HTML tables require an actual `src` URI and may repeat payloads in the standalone Markdown; ZIP export deduplicates those too.

## Configuration and export

```python
from pathlib import Path
from document_converter.core.options import ConversionOptions
from document_converter.core.router import ConverterRouter
from document_converter.services.markdown_exporter import MarkdownExporter
from document_converter.services.asset_package import AssetPackageExporter

options = ConversionOptions(
    media_placement="context",  # default; "appendix" collects visuals at the end
    pdf_mode="pages",           # existing default; alternatives: "images", "text"
)
result = ConverterRouter(options=options).convert(Path("report.docx"))
MarkdownExporter().export(result.markdown, Path("report.md"))
AssetPackageExporter().export(result.markdown, Path("report.zip"))
```

The GUI now receives contextual media automatically through its existing router. Advanced placement/PDF choices and ZIP export are available through the core API. No new GUI control is implied.

ZIP layout:

```text
report.zip
├── document.md
└── assets/
    └── <sha256>.png
```

Extract the ZIP and move the Markdown together with `assets/`. Filenames are derived from the complete content hash, preventing original-name collisions. The same bytes and MIME type reuse one file. The exporter rewrites generated image syntax without changing fenced, indented, or single-line inline-code examples. It does not crawl hyperlinks, fetch remote images, or promise to parse every Markdown dialect. Original URI examples inside code remain literal examples.

ZIP publication retains overwrite protection and temporary-file cleanup. Malformed Base64 is rejected before publishing; failure to replace an existing target leaves it untouched. Base64 output remains subject to the configured output budget. This work adds no hard process RAM/time sandbox.

## Implementation map

- `core/models.py`: optional inline-image and page-slot metadata with compatible defaults.
- `embedded_media/placement.py`: opaque position markers collected during native parsing.
- `converters/semantic_office.py`: Word image callbacks and PowerPoint picture conversion preserve exact occurrences and alt text.
- `converters/office_structure.py` / `faithful_converter.py`: worksheet/drawing relationship resolution, original bytes and cell locations.
- `converters/layout_pdf.py` / `embedded_media/extractor.py`: page markers and explicit page numbers on extracted visuals.
- `embedded_media/converter.py`: marker resolution, Base64 deduplication, fallback warnings and source provenance.
- `services/asset_package.py`: portable image-reference rewriting for Markdown and HTML while protecting code examples.
- `tests/test_q4_media.py`: source-order, portability, failure and byte-preservation acceptance.

Opaque markers are removed from final results, and temporary media files are not referenced by exported Markdown. The final conversion result contains Markdown/warnings rather than retaining the temporary inline binary metadata.

## Validation actually performed

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_q4_media.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
git diff --check
```

Final full-suite result: **150 passed in 40.04s** on the Windows development environment. This is a test duration, not a conversion performance benchmark. Coverage includes:

- two uses of one Word image with separate source captions and only one payload;
- a Word image inside a merged HTML table and its packaged `src`;
- PowerPoint image/caption ordering on two slides;
- selected Excel sheets both with and without their own image;
- two-page PDF placement under all three visual modes;
- native JPEG byte round-trip from a PDF image stream;
- appendix compatibility, missing-position fallback, unsupported MIME warnings, output-budget rejection;
- package deduplication/reference resolution, untouched code examples, malformed Base64 and failed overwrite.

## Before / after and next work

Previously, most OOXML/PDF visuals were detached into a final appendix. Supported source positions now render in their document, slide, worksheet or page context. The former generic ZIP rewrite did not cover reference definitions or HTML table images; these generated forms now resolve to packaged assets while code examples remain unchanged.

Conversion profiles were evaluated and are not added in Q4: the explicit placement, PDF, text and spreadsheet options already express the supported policies, while named presets would currently suggest fidelity guarantees not established by tests. OCR remains excluded in accordance with the project's existing scope.

Q4 closes this documented source-context and packaging scope. Q5 follows with broader corpus/stress evaluation, cancellation within a file, and stronger performance/offline checks. Arbitrary image-caption inference or interpretation is not claimed.
