# Q5 — Testing, performance and reliability

Completed on 2026-11-11 for the scope below. **205 tests passed in 40.50 seconds** on Windows 11 / Python 3.13.0. The evaluation runner passed **42/42 case runs**: ten formats and four stress cases, each repeated three times in a fresh process. This is a regression baseline, not a general document accuracy score. User audit is the next checkpoint.

## Checkpoints and evidence

| Checkpoint | Delivered | Evidence |
|---|---|---|
| Q5A — Source comparison | Fixed semantic goldens for ten supported extensions; exact text where appropriate, source ordering, table values, asset hashes and ZIP references | `tests/fixtures/q5/golden.json`, `tools/q5_corpus.py`; previous Q3/Q4 complex-layout regressions retained |
| Q5B — Reliability | Active-file cancellation, 120-second per-file deadline, independent parser process, cleanup on success/failure/cancellation | `tests/test_q5_reliability.py`: real workers, sleeping/crashing child injection, batch continuation and restart |
| Q5C — Offline and GUI | Python network guard before parser imports, generic private error messages, usable GUI event loop during conversion | DNS/TCP/UDP denied, all ten parsers evaluated with guard; Qt timer advances while active child is cancelled |
| Q5D — Performance | Lazy parser loading and one-pass Excel cached-value reading; reproducible time and peak-process-memory report | [Raw measurements](benchmarks/q5-windows.json), 14 cases × 3 runs |

## What changed and why

The GUI's existing `QThread` now supervises a disposable Python process for each file. The child receives the source path and options through a private temporary request, returns UTF-8 Markdown plus warning metadata, and never writes the final export. The parent polls every 50 ms. Cancellation or timeout terminates and joins the child before removing its scratch directory. All parser temporary directories inherit that scratch root.

No unsafe thread termination is used. A parser failure becomes one file outcome, so subsequent files can continue. Cancellation instead skips the remaining files and retains completed outcomes. The default deadline is **120 seconds per file**, including Python startup and parser imports. The deadline does not impose a hard memory limit.

Parser stdout/stderr are not published or logged. Exception text can contain document content, so worker diagnostics expose the exception class and a general recovery hint. Missing imports suggest reinstalling requirements. This improves privacy but provides less detail than direct API debugging.

| Before | After |
|---|---|
| Cancel waited for the current parser to return | Cancel terminates the active built-in worker; completed results survive |
| A hung parser could keep the batch busy indefinitely | Each built-in file has a configurable deadline; the next file can proceed |
| Creating the default router imported every parser and initialized an unused fallback engine | Imports happen only when the corresponding format is converted |
| Read-only XLSX cache was randomly accessed for each formula | Cached worksheet rows are streamed once alongside formula rows |
| Ten-format runner checked a small marker | Source-derived semantic predicates, exact text, image hashes, references and bounded stress gates are evaluated |

No dependency, OCR engine, cloud API or model was added. Advanced format/ZIP options remain API features; the GUI keeps its existing format selector and single-file Base64 output.

## Core API

```python
from pathlib import Path
from document_converter.core.options import ConversionOptions
from document_converter.services.batch_converter import BatchConverter
from document_converter.services.process_converter import ProcessConverter

options = ConversionOptions(pdf_mode="images")
batch = BatchConverter(options=options, timeout_seconds=180)
results = batch.convert([Path("first.pdf"), Path("second.pdf")])

# Call batch.cancel() from another thread while convert() is running.
# Before a subsequent run:
batch.reset_cancellation()

single = ProcessConverter(options, timeout_seconds=180).convert(Path("first.pdf"))
```

`ConverterRouter.convert()` stays synchronous for existing API callers. It does **not** install the network guard or deadline. Passing a custom router to `BatchConverter(router=...)` retains the original in-process extension point and cancellation between files; arbitrary custom converter objects are not serialized into workers.

## Corpus and metrics

The goldens are source-authored expectations checked into Git, not snapshots automatically blessed from converter output. Binary Office/PDF fixtures are generated from known source values. These are synthetic fixtures; no private documents or external datasets are committed. Existing Q3 cases cover merged/nested Word tables, notes, numbering, PDF geometry and PowerPoint connector/chart records. Q4 retains image byte/placement and export failure cases.

| Measurement | Definition |
|---|---|
| Exact decoded text | Output string equals source text for TXT, or the hand-authored fenced expectation for JSON/XML; BOM/encoding bytes are outside this contract |
| Semantic fragments | Each expected heading, cell value, merge or note fragment occurs in output; forbidden script/scheme fragments do not |
| Source order | Every expected marker appears, with strictly increasing first positions |
| Table fidelity under stress | Number of complete expected data rows equals the source row count; CSV also contains the original source text |
| Media fidelity | Decoded Base64 SHA-256 equals the generated source image hash; packaged image bytes match, and all generated asset references resolve inside the ZIP |
| Offline check | No outbound Python DNS/connect/sendto audit events occur; the guard denies these operations if attempted |
| Duration | Time around router construction/import/conversion; excludes fixture generation and Python startup, unlike the production deadline |
| Peak memory | OS-reported peak resident/working-set memory of the child, including imports, fixture generation, conversion and asset validation; not GUI-plus-child total |
| Gate result | Every boolean check must pass; a failed check, child failure or 120-second runner timeout produces a nonzero exit code |

`urllib3` performs a local IPv6 bind probe during some imports. The guard blocks it and the report counts it separately as `blocked_local_bind_probes`. It is not an outbound request. The guard covers Python socket audit events, not native-library network APIs; no OS sandbox or complete security audit is claimed.

JSON/XML intentionally preserve malformed input as source code rather than validating or repairing it. Malformed binary containers/PDF and unterminated CSV fields fail explicitly. Empty valid containers and text sources are tested separately from corrupt files. Markdown checks cover generated structures and references, not full CommonMark conformance across every viewer.

## Recorded performance

Three fresh-process measurements per case on Windows 11 / Python 3.13.0; medians below. Peak bytes are the maximum across those three runs. Results depend on hardware, background load, parser versions and document structure. Three runs are insufficient for a p95 claim. There is no promised consumer RAM budget or universal performance target.

| Case | Source scale | Median seconds | Maximum process peak bytes |
|---|---|---:|---:|
| TXT golden | Unicode, CRLF, code and trailing spaces | 0.024823 | 24,260,608 |
| DOCX golden | Heading, list, merged table, caption and image | 1.437711 | 144,519,168 |
| PPTX golden | Two slides, table, note and image | 1.198399 | 128,675,840 |
| XLSX golden | Two sheets, formula, merge and anchored image | 0.047457 | 46,182,400 |
| TXT stress | 100,000 Unicode lines plus end marker | 0.036611 | 34,877,440 |
| CSV stress | 20,000 data rows × 3 columns | 0.127799 | 33,144,832 |
| XLSX stress | 5,000 data rows × 3 columns, 5,000 formulas | 0.503206 | 78,618,624 |
| PDF stress | 30 generated text pages, text mode | 0.304838 | 43,847,680 |

The Excel stress fixture **timed out at 120 seconds before the cache fix** during this Q5 run. After the fix, all three runs completed, with a median of 0.503206 seconds. The earlier timeout is a lower bound, not a measured completion time; no exact speedup ratio is claimed. Default high-resolution PDF page rendering and arbitrarily large Office files are not represented by this text-mode PDF stress case.

## Reproduce and review

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe tools\evaluate_q5.py --repeat 3 --output docs/benchmarks/q5-windows.json
.\.venv\Scripts\python.exe tools\evaluate_q5.py --case stress-xlsx
git diff --check
```

The runner writes no source-document contents to its report. It removes generated source/output fixtures on completion. The checked-in report deliberately records no personal filesystem paths. Re-running with `--output` replaces that benchmark report; review the diff before committing new measurements.

| Implementation | Purpose |
|---|---|
| `services/process_converter.py`, `conversion_worker.py` | Child lifecycle, deadline, private scratch and result transfer |
| `services/offline.py` | Per-worker Python socket guard |
| `services/batch_converter.py`, `gui/main_window.py` | Existing batch workflow and active cancellation button |
| `core/router.py` | Deferred parser imports; custom mappings remain supported |
| `converters/faithful_converter.py` | One-pass Excel cache scan |
| `tools/q5_corpus.py`, `evaluate_q5.py`, golden JSON | Source generation, explicit oracles and measurements |
| `tests/test_q5_reliability.py`, `tests/test_gui.py` | 55 additional cases beyond the Q4 baseline |

## User audit

| Workflow to review | Expected behavior |
|---|---|
| Add, remove, clear and select each supported type | Same-extension batch policy, TXT initial selection, clear errors for unsupported files |
| Convert and compare source | Text, headings, numbers, tables, notes and media follow the documented Q3/Q4 policies |
| Cancel a long-running conversion | Window remains usable; active and pending files cancel; completed results remain saveable |
| Mix valid and broken files of the same extension | Failed file is reported; successful files remain available |
| Preview, Copy and Save a large result | Preview stops at 200,000 characters; Copy/Save include the full output |
| Save Markdown and API asset ZIP | Existing overwrite rules hold; images/references resolve according to the chosen export mode |
| Repeat conversion after a cancellation | A new GUI run resets cancellation; results can be produced normally |

Record the source format, chosen options, expected content, observed difference and minimal non-sensitive reproduction for any finding. Fixes should gain regression cases. This audit can reveal gaps beyond the generated corpus and is not represented as already completed.

Remaining limits: no hard RAM sandbox, no native-network interception proof, no exhaustive fuzzing, no real-world accuracy guarantee, and no installer/frozen-executable or cross-platform verification in Q5. Temporary data is removed through normal process cleanup, not secure erasure or power-loss recovery. A new child per file adds startup overhead. Q6/F will validate clean installation, frozen worker launching, dependencies/licenses and packaging after user audit.
