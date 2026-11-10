<div align="center">

<img src="assets/branding/app-logo.png" alt="Hybrid Document to Markdown logo" width="128">

# 📄 Hybrid Document to Markdown

### A local-first Windows desktop converter powered by Python and Microsoft MarkItDown

[![Development Status](https://img.shields.io/badge/status-Quality%20Q2%20WIP-D97706?style=for-the-badge)](#-roadmap)
[![Tests](https://img.shields.io/badge/tests-92%20passed-16A34A?style=for-the-badge&logo=pytest&logoColor=white)](#-testing)
[![Python](https://img.shields.io/badge/python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](#-technology-stack)

[![MarkItDown](https://img.shields.io/badge/MarkItDown-0.1.9-2563EB?style=flat-square)](https://github.com/microsoft/markitdown)
[![PySide6](https://img.shields.io/badge/PySide6-6.12-41CD52?style=flat-square&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D4?style=flat-square&logo=windows&logoColor=white)](#-requirements)
[![License](https://img.shields.io/badge/license-MIT-F59E0B?style=flat-square)](LICENSE)

**Convert common documents into readable Markdown without rebuilding format-specific parsers from scratch.**<br>
**The project combines a tested conversion core with a beginner-friendly Windows desktop workflow.**

[Overview](#-overview) •
[Features](#-feature-status) •
[Formats](#-supported-formats) •
[Quick Start](#-quick-start) •
[Architecture](#-architecture) •
[Roadmap](#-roadmap)

</div>

---

> [!IMPORTANT]
> Phase E's single-file image workflow is implemented. Conversion quality hardening is now in progress: Q1 audit and the first whitespace fix are complete; Q2 shared quality infrastructure is WIP. Conversion remains local, with Base64 support and no configured OCR, model training, or cloud inference. See the [evidence-based audit](docs/CONVERSION_QUALITY_AUDIT.md) and [changelog](CHANGELOG.md).

> [!NOTE]
> This is an independent portfolio project that uses [Microsoft MarkItDown](https://github.com/microsoft/markitdown). It is not an official Microsoft product and is not affiliated with or endorsed by Microsoft.

## 📚 Table of Contents

- [Overview](#-overview)
- [Feature Status](#-feature-status)
- [Supported Formats](#-supported-formats)
- [How Conversion Works](#-how-conversion-works)
- [Quick Start](#-quick-start)
  - [Requirements](#-requirements)
  - [Installation](#-installation)
  - [Run the Desktop App](#-run-the-desktop-app)
  - [Run the Tests](#-run-the-tests)
  - [Use the Core API](#-use-the-core-api)
- [Batch Rules and Validation](#-batch-rules-and-validation)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Privacy and Limitations](#-privacy-and-limitations)
- [Technology Stack](#-technology-stack)
- [Roadmap](#-roadmap)
- [Engineering Principles](#-engineering-principles)
- [License and Credits](#-license-and-credits)

## 🔎 Overview

<table>
<tr>
<td width="50%" valign="top">
<h3>🎯 What it does</h3>
<p>Hybrid Document to Markdown converts common documents into Markdown (<code>.md</code>). It targets users who want a clear Windows workflow instead of manual conversion commands.</p>
<ul>
<li>Validates local documents</li>
<li>Routes multiple file formats</li>
<li>Processes safe same-extension batches</li>
<li>Preserves independent file outcomes</li>
<li>Exports UTF-8 Markdown</li>
</ul>
</td>
<td width="50%" valign="top">
<h3>💡 Why it exists</h3>
<p>Maintaining a custom parser for every format is expensive. This project delegates parsing to MarkItDown and focuses on user experience, reliability, testing, and Windows delivery.</p>
<ul>
<li>Local-first processing</li>
<li>Predictable validation</li>
<li>Transparent errors</li>
<li>PySide6 desktop usability</li>
<li>Reproducible integration tests</li>
</ul>
</td>
</tr>
</table>

> [!NOTE]
> Earlier custom TXT-converter code remains as a learning milestone. MarkItDown is the production engine.

## ✨ Feature Status

<table>
<tr>
<td width="50%" valign="top">
<h3>✅ Implemented</h3>
<ul>
<li>Multi-format conversion core</li>
<li>Same-extension batch conversion</li>
<li>Independent per-file outcomes</li>
<li>Existence, type, extension, size, and readability validation</li>
<li>UTF-8 Markdown export with overwrite protection</li>
<li>Accessible file picker and drag and drop</li>
<li>Threaded conversion with per-file status</li>
<li>Markdown preview, copy, and collision-safe export</li>
<li>Low-glare dark-medieval pixel theme with a TXT-first file selector</li>
<li>Custom transparent pixel-art application and header logo</li>
<li>Scrollbars that appear only when content overflows</li>
<li>Progressive “Save Markdown” action shown after successful conversion</li>
<li>Automatic DOCX, PPTX, and XLSX embedded-image extraction</li>
<li>Automatic local PDF-page rendering</li>
<li>PNG, JPEG, GIF, WebP, BMP, TIFF, and SVG data-URI support</li>
<li>Single-file Markdown output with Base64-embedded images</li>
<li>No OCR runtime, model pack, dataset, or training requirement</li>
<li>Real DOCX image-to-Base64 integration coverage</li>
<li>92 passing automated tests; complex-format fidelity is still being improved</li>
</ul>
</td>
<td width="50%" valign="top">
<h3>🚧 WIP &amp; planned</h3>
<ul>
<li><strong>Completed — Phase E:</strong> preserve images inside one Markdown file</li>
<li><strong>WIP — Quality Q2:</strong> shared quality infrastructure after the Q1 audit</li>
<li><strong>Planned — Phase F:</strong> Windows packaging after quality hardening</li>
<li><strong>Planned:</strong> compatibility testing with major multimodal AI clients</li>
</ul>
</td>
</tr>
</table>

## 🗃️ Supported Formats

Representative integration coverage exists for every MVP format.

| Category | Extensions | Dependency path | Verification |
|---|---|---|:---:|
| Plain text | `.txt` | MarkItDown core | ✅ Passed |
| Word | `.docx` | `markitdown[docx]` | ✅ Passed |
| PDF | `.pdf` | `markitdown[pdf]` | ✅ Text-based PDF passed |
| PowerPoint | `.pptx` | `markitdown[pptx]` | ✅ Passed |
| Excel | `.xlsx` | `markitdown[xlsx]` | ✅ Passed |
| Tabular data | `.csv` | MarkItDown core | ✅ Passed |
| Web documents | `.html`, `.htm` | MarkItDown core | ✅ Passed |
| Structured text | `.json`, `.xml` | MarkItDown core | ✅ Passed |

> [!WARNING]
> “Supported” does not mean perfect visual fidelity. Embedded images are preserved as Base64, not interpreted. Whether an AI chat decodes a Markdown data URI depends on that platform.

Emails, archives, audio, EPUB, LOG files, and standalone image conversion are outside the committed MVP scope.

## 🔄 How Conversion Works

```mermaid
flowchart LR
    A[Local documents] --> B[File validation]
    B --> C{Same extension?}
    C -- No --> X[Reject batch]
    C -- Yes --> D[Converter router]
    D --> E[Microsoft MarkItDown text conversion]
    D --> I[Local document image extraction]
    I --> O[Base64 data URI encoding]
    E --> M[Merge into one Markdown file]
    O --> M
    M --> F[Per-file outcomes]
    F --> G[Markdown export]
    G --> H[One .md file per input]

    UI[PySide6 GUI] -. controls .-> A
```

The conversion path is fully local. MarkItDown converts document text, while `DocumentImageExtractor` retrieves OOXML media or renders PDF pages. `EmbeddedMediaDocumentConverter` encodes each image as a Base64 `data:` URI and appends it to the same Markdown result.

## 🚀 Quick Start

<table>
<tr>
<td width="38%" valign="top">
<h3 id="requirements">📋 Requirements</h3>
<ul>
<li>Windows 10 or 11</li>
<li>Python 3.13</li>
<li>Git and PowerShell</li>
<li>Internet during installation</li>
</ul>
<p>No API key is required for local conversion.</p>
<h3 id="run-the-tests">🧪 Test</h3>
<pre><code>python -m pytest -q</code></pre>
<p>Last verified: <code>92 passed</code> (2026-11-10)</p>
</td>
<td width="62%" valign="top">
<h3 id="installation">📦 Installation</h3>
<pre><code>git clone https://github.com/DrBham/Hybird-Document-To-Markdown.git
cd Hybird-Document-To-Markdown

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
python -m pip check</code></pre>
<p>Activate <code>.venv</code> before developing or testing so project packages stay isolated.</p>
</td>
</tr>
</table>

> [!NOTE]
> The root-level `pytest.ini` adds `src` to pytest's import path. It is configuration, not a generated cache file.

### 🖥️ Run the Desktop App

From the repository root with the virtual environment active:

```powershell
$env:PYTHONPATH = "src"
python -m document_converter
```

The file-type selector starts at TXT. Choose another format when needed, then browse or drag matching documents, convert them, review a result, and choose an output folder. “Save Markdown” appears after at least one conversion succeeds. Conversion runs in a worker thread, so the window remains responsive.

### 🖼️ Single-File Image Embedding

Image embedding is automatic for PDF, DOCX, PPTX, and XLSX inputs. No separate runtime or model installation is required.

The generated Markdown contains entries such as:

```markdown
![Embedded image: diagram.png](data:image/png;base64,iVBORw0KGgo...)
```

The characters after `base64,` encode the extracted image bytes. Supported OOXML media are copied without recompression; PDF images in this workflow are newly rendered page PNGs, not the original embedded image bytes. Decoding or displaying these payloads depends on the receiving client; uploading a `.md` file does not guarantee that an AI chat will inspect its images.

> [!IMPORTANT]
> Base64 is encoding, not encryption or OCR. It preserves the original visual but does not describe its meaning. Uploading the Markdown to a third-party AI also subjects its contents to that provider's privacy policy.

> [!WARNING]
> Base64 increases binary size by roughly one third, and not every AI chat accepts or renders data URIs from an uploaded `.md` file. Large PDFs can therefore produce very large Markdown files.

### 🧑‍💻 Use the Core API

> [!NOTE]
> The desktop app is the recommended interactive workflow. The examples below show how to reuse the tested Python core directly.

Convert one file:

```python
from pathlib import Path

from document_converter.core.router import ConverterRouter
from document_converter.services.markdown_exporter import MarkdownExporter


source = Path("documents/report.pdf")

conversion = ConverterRouter().convert(source)
output = source.with_suffix(".md")

MarkdownExporter().export(
    conversion.markdown,
    output,
    overwrite=False,
)

print(f"Saved: {output}")
```

Convert a same-extension batch:

```python
from pathlib import Path

from document_converter.services.batch_converter import BatchConverter


files = [
    Path("documents/report.pdf"),
    Path("documents/manual.pdf"),
    Path("documents/tutorial.PDF"),
]

batch = BatchConverter().convert(files)

for outcome in batch.outcomes:
    if outcome.succeeded:
        print(f"Converted: {outcome.source_path.name}")
    else:
        print(f"Failed: {outcome.source_path.name} — {outcome.error}")
```

When running a standalone development script from the repository root, expose the `src` directory first:

```powershell
$env:PYTHONPATH = "src"
python .\your_script.py
```

## 🛡️ Batch Rules and Validation

<table>
<tr>
<td width="50%" valign="top">
<h3>📚 Batch rules</h3>
<ul>
<li>At least one file is required.</li>
<li>All extensions must match, ignoring case.</li>
<li>Each file converts independently.</li>
<li>Successful results survive other failures.</li>
<li>Files are never merged automatically.</li>
</ul>
<p><strong>Allowed:</strong> <code>report.pdf</code>, <code>manual.PDF</code></p>
<p><strong>Rejected:</strong> <code>report.pdf</code>, <code>slides.pptx</code></p>
</td>
<td width="50%" valign="top">
<h3>🛡️ File validation</h3>
<ul>
<li>The path exists.</li>
<li>The path points to a file.</li>
<li>The extension is on the MVP allowlist.</li>
<li>The file is no larger than 100 MiB.</li>
<li>The file can be opened for reading.</li>
</ul>
<p>Validation happens before MarkItDown receives the document.</p>
</td>
</tr>
</table>

## 🏗️ Architecture

| Layer | Responsibility | Main components |
|---|---|---|
| Core models | Stable application-level results | `ConversionResult`, `FileConversionOutcome`, `BatchConversionResult` |
| Validation | Reject invalid input early | `validate_file()` |
| Routing | Select the converter by extension | `ConverterRouter` |
| Conversion adapter | Isolate the third-party engine | `MarkItDownConverter` |
| Services | Coordinate batches and export | `BatchConverter`, `MarkdownExporter` |
| Image extraction | Extract OOXML media and render PDF pages locally | `DocumentImageExtractor` |
| Media embedding | Encode images as Base64 data URIs and append them to Markdown | `EmbeddedMediaDocumentConverter` |
| GUI | Desktop interaction | PySide6 window, worker thread, preview, and export workflow |

### Why an adapter?

`MarkItDownConverter` keeps third-party details behind the project's `BaseConverter` interface. The rest of the application works with its own models instead of depending directly on MarkItDown internals.

This design provides:

- Easier unit testing with fake engines
- Clear ownership boundaries
- Lower migration cost if the engine API changes
- Reusable core logic for the desktop GUI and future integrations

## 🗂️ Project Structure

```text
.
├── src/
│   └── document_converter/
│       ├── __main__.py
│       ├── converters/
│       │   ├── markitdown_converter.py
│       │   └── txt_converter.py
│       ├── core/
│       │   ├── base_converter.py
│       │   ├── models.py
│       │   ├── router.py
│       │   └── validator.py
│       ├── gui/
│       │   ├── app.py
│       │   ├── main_window.py
│       │   └── theme.py
│       ├── embedded_media/
│       │   ├── converter.py
│       │   └── extractor.py
│       └── services/
│           ├── batch_converter.py
│           └── markdown_exporter.py
├── design-system/
│   └── hybrid-document-to-markdown/
│       └── MASTER.md
├── assets/
│   ├── branding/
│   │   └── app-logo.png
│   └── fonts/
│       ├── PressStart2P-Regular.ttf
│       ├── PressStart2P-OFL.txt
│       └── PressStart2P-FONTLOG.txt
├── tests/
├── tools/audit_conversion_quality.py
├── docs/CONVERSION_QUALITY_AUDIT.md
├── CHANGELOG.md
├── pytest.ini
├── requirements.in
├── requirements.txt
├── THIRD_PARTY_NOTICES.md
└── README.md
```

## 🧪 Testing

The test suite focuses on application behavior and third-party integration boundaries. It does not pretend to test MarkItDown's internal algorithms as original project code.

Audit baseline: **80 passed**. After preserving whitespace in the media decorator: **92 passed**, including the offscreen GUI conversion/export workflow. Eight regression cases fail against the old decorator. Passing smoke tests do not establish source fidelity for complex documents.

Run reproducible synthetic probes with `python tools/audit_conversion_quality.py`. The script prints source/output comparisons and removes its temporary fixtures; it is not an accuracy benchmark. See the [audit](docs/CONVERSION_QUALITY_AUDIT.md) for observed losses and the measurement plan.

<table>
<tr>
<td width="50%" valign="top">
<h3>🔌 Integration coverage</h3>
<ul>
<li>All agreed MVP extensions</li>
<li>Real TXT, DOCX, and text-based PDF conversion</li>
<li>Real PPTX and XLSX conversion</li>
<li>Real CSV, HTML/HTM, JSON, and XML conversion</li>
</ul>
</td>
<td width="50%" valign="top">
<h3>⚙️ Behavior coverage</h3>
<ul>
<li>Invalid, oversized, and unreadable files</li>
<li>Case-insensitive and mixed-extension batches</li>
<li>Partial failures and result preservation</li>
<li>Unicode export and overwrite protection</li>
<li>GUI selection, state, threaded conversion, and export workflow</li>
<li>OOXML media extraction for DOCX, PPTX, and XLSX</li>
<li>PDF-page rendering and Base64 data-URI generation</li>
<li>Real DOCX image embedding through the default router</li>
</ul>
</td>
</tr>
</table>

Run the full suite with:

```powershell
python -m pytest -q
```

> [!NOTE]
> A local passing test badge is shown at the top because this repository does not yet have a GitHub Actions workflow. A live CI badge should replace it after CI is configured.

## 🔐 Privacy and Limitations

<table>
<tr>
<td width="50%" valign="top">
<h3>🔒 Local-first privacy</h3>
<ul>
<li>Conversion and image embedding need no API key.</li>
<li>Documents are not uploaded by the application.</li>
<li>The application does not configure or use an OCR model, training dataset, or inference runtime.</li>
<li>Images are encoded locally and remain inside the exported Markdown.</li>
<li>Users choose whether to upload the result to a third-party AI.</li>
</ul>
</td>
<td width="50%" valign="top">
<h3>⚠️ Current limitations</h3>
<ul>
<li>A packaged <code>.exe</code> is not available yet.</li>
<li>Not every Markdown renderer or AI chat supports Base64 data URIs.</li>
<li>Base64 output is larger than the original binary image data.</li>
<li>The application preserves images but does not interpret diagrams or run OCR.</li>
<li>Complex layouts may lose fidelity.</li>
<li>XLSX conversion can change string identifiers and numeric representation, and omit formulas.</li>
<li>Upstream whitespace normalization still affects TXT and preformatted content; the media decorator now preserves its input exactly.</li>
<li>CSV multiline cells and non-comma delimiters need improvement; JSON/XML are not yet fenced.</li>
<li>Images are appended without source placement; local HTML assets are not packaged.</li>
<li>PDF renders every page; decompressed data, page pixels, and output size do not yet have explicit budgets.</li>
<li>Encrypted or damaged files may fail.</li>
<li>The 100 MiB limit is not yet configurable in the GUI.</li>
</ul>
</td>
</tr>
</table>

> [!IMPORTANT]
> Conversion remains local, but privacy is no longer under this application's control after a user uploads the exported Markdown to ChatGPT, Claude, or another external service.

## 🧰 Technology Stack

| Area | Technology | Current role |
|---|---|---|
| Language | Python 3.13 | Application and tests |
| Desktop GUI | PySide6 6.12 | Implemented Phase D workflow |
| Conversion | Microsoft MarkItDown 0.1.9 | Production conversion engine |
| Embedded media | Python Base64 + local OOXML/PDF extraction | Preserve images inside one `.md` file |
| DOCX | Mammoth through `markitdown[docx]` | Word conversion |
| PDF | pdfminer.six and pdfplumber through `markitdown[pdf]` | Text-based PDF conversion |
| PowerPoint | python-pptx through `markitdown[pptx]` | PPTX conversion |
| Excel | pandas and openpyxl through `markitdown[xlsx]` | XLSX conversion |
| Testing | pytest | Unit and integration tests |
| Version control | Git and GitHub | History and collaboration |
| Target OS | Windows | Development and release target |

Direct dependencies are declared in `requirements.in`; the reproducible development snapshot is pinned in `requirements.txt`. There is no separate machine-learning dependency layer.

## 🗺️ Roadmap

| Phase | Deliverable | Status |
|---|---|:---:|
| Foundation (00–A) | Repository, environment, architecture, TXT learning milestone, and scope/documentation migration | ✅ Completed |
| B — Engine | MarkItDown integration and initial TXT/DOCX/PDF verification | ✅ Completed |
| C — Conversion core | All MVP formats, validation, same-extension batches, per-file outcomes, and export | ✅ Completed |
| D — Desktop GUI | Format selection, drag and drop, threaded conversion, status list, preview, Save Markdown workflow, theme, and branding | ✅ Completed |
| E — Single-file media preservation | Extract document images and embed them as Base64 data URIs in the same Markdown file | ✅ Completed |
| Quality Q1 | Architecture audit, synthetic fidelity probes, first whitespace regression fix | ✅ Completed |
| Quality Q2 | Compatible options/warnings, atomic export, resource limits, shared serialization checks | 🚧 WIP |
| Quality Q3 | Incremental fidelity improvements for all supported formats | Planned |
| Quality Q4 | Contextual assets, configurable Base64/assets export, PDF image modes | Planned |
| Quality Q5 | Corpus evaluation, performance, cancellation, security/offline regression | Planned |
| Quality Q6 / F — Release | Documentation, clean-install checks, Windows packaging, license inventory, compatibility and release validation | Planned after quality gates |

### Phase E result

- Images are embedded automatically; there is no GUI model toggle.
- DOCX, PPTX, and XLSX media are read directly from their OOXML containers.
- PDF pages are rendered locally and embedded as PNG data URIs.
- PNG, JPEG, GIF, WebP, BMP, TIFF, and SVG are supported.
- Text and image payloads stay together in one `.md` file.
- PaddleOCR, model packs, datasets, training scripts, and ML dependencies were removed.
- Real DOCX image embedding and local PDF rendering are covered by tests.

### Current: Quality Q2

1. Define backward-compatible conversion options and structured warnings.
2. Make export atomic while retaining overwrite protection.
3. Bound decompression/rendering/output resources and verify cleanup on failure.
4. Add targeted serialization checks, then improve format-specific fidelity in Q3.

Q2 is the active work phase; its implementation checkpoints are still pending. The [full audit and roadmap](docs/CONVERSION_QUALITY_AUDIT.md) defines evidence, severity, regression risk, Phase 1 checkpoints, and acceptance gates. Base64 remains available. Installer work follows these quality gates.

> [!IMPORTANT]
> Base64 round-trip preservation is tested for supported extracted media, including a real DOCX PNG. This does not guarantee that every visual element is extracted, that PDF rasterization is lossless, or that an external AI platform will decode images from an uploaded `.md` file.

Development follows this milestone cycle:

```text
Implement → Test → Document → Commit → Push
```

After a phase is complete, the next phase becomes WIP.

## 🧭 Engineering Principles

- Finish the application before expanding its scope.
- Prefer simple, testable modules over speculative abstractions.
- Reuse mature libraries instead of rebuilding their algorithms.
- Keep local conversion available without cloud credentials.
- Preserve successful batch results when another file fails.
- Never claim perfect conversion fidelity.
- Treat third-party output and errors as integration boundaries.
- Keep secrets and generated files out of Git.
- Document implemented and planned features separately.

## 📜 License and Credits

Original project code and documentation are licensed under the [MIT License](LICENSE), where the contributors own the applicable rights.

Third-party components remain under their own licenses. Review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the current dependency inventory and release-audit checklist.

### Credits

- [Microsoft MarkItDown](https://github.com/microsoft/markitdown) — document-to-Markdown conversion engine
- [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/) — Windows desktop framework
- [pytest](https://docs.pytest.org/) — automated testing

---

<div align="center">

**Built as a practical Python portfolio project with transparent scope, reproducible tests, and local-first design.**

</div>
