# Q6 Checkpoint 1 — Drag-and-drop P0

Completed on 2026-11-17 for the automated acceptance scope below. The full suite passes: **220 tests in 47.16 seconds**. Q6 remains in progress because native Explorer acceptance, shared output policies, format-quality improvements, and per-format scoring remain.

## 1. Objective

Restore dependable drag-and-drop without changing the same-extension batch model or breaking Browse/Select File. A dropped file should be recognized from its own extension even when the GUI starts with the TXT selector.

## 2. Root cause

`DropZone.dropEvent()` emitted valid local paths into the same `add_files()` path used by Browse. `add_files()` correctly applies the selected file-type filter, but the selector starts at `.txt`. Therefore a PDF, DOCX, or other supported file dropped before manually changing the selector was rejected as a mismatch. Drag enter also accepted any URL payload, had no explicit drag-move policy, and deferred useful validation until after drop.

Affected code: `src/document_converter/gui/main_window.py`, especially `DropZone` and `MainWindow.add_files()`. Severity: P0 because the primary direct-manipulation workflow appeared nonfunctional. Regression risk: batch type selection and Browse filtering.

## 3. Implementation

- Browse keeps its explicit selector filter.
- Drop extracts decoded local paths from Qt URL payloads and checks that an existing file has a supported extension.
- A new dropped-file route detects the single supported extension, updates the selector, then reuses the established `add_files()` validation and list updates.
- Same-type multiple files are accepted. Mixed supported formats are rejected before any list state changes. Unsupported or missing entries are skipped and reported when a valid same-type batch remains.
- Drag enter and drag move provide acceptance feedback only for supported local files. Drop never starts conversion automatically.
- GUI help and accessibility text explain that the selector filters Browse while Drop detects type automatically.

No dependency, converter behavior, document output, or export policy changed.

## 4. Modified files

| File | Change |
|---|---|
| `src/document_converter/gui/main_window.py` | URL parsing, drag-enter/move/drop validation, automatic dropped-type selection, mixed-format handling, and help text |
| `tests/test_gui.py` | Fifteen Q6 cases, including ten extension parameters and Browse regression |
| `README.md`, `CHANGELOG.md`, quality reports | Q6 status, evidence, limitations, and next checkpoint |

## 5. Tests performed

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gui.py -q -p no:cacheprovider
# 27 passed

.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
# 220 passed in 47.16s
```

The automated matrix covers TXT, DOCX, PDF, PPTX, XLSX, CSV, HTML, HTM, JSON, and XML; uppercase extensions; spaces; Unicode filenames; multiple same-type files; unsupported URLs; non-URL payloads; mixed supported formats; visual drag state; and the Browse path.

## 6. Before / after evidence

| Scenario | Before | After |
|---|---|---|
| Drop PDF while selector starts at TXT | Rejected as not matching `.TXT` | PDF is detected, selector changes to PDF, file becomes Pending |
| Drop same-type batch | Depended on manually matching selector | Extension detected once; valid files are added together |
| Drop mixed PDF and DOCX | Filter-dependent partial interpretation | Entire drop rejected with a one-format-per-batch message |
| Drop unsupported-only payload | Drag looked acceptable until drop | Drag enter is rejected; drop route also reports supported formats |
| Browse PDF with PDF filter | Existing behavior | Still adds the selected PDF |

## 7. Regression status

The complete 220-test suite passes. Conversion workers, all format converters, preview, cancellation, Base64 media, ZIP export, and atomic Markdown export retain their existing tests. The selector continues to constrain Browse, and the file list continues to enforce one extension per batch.

## 8. Quality result

The automated P0 functional gate passes for all ten supported extensions. This is not a 90/100 conversion-quality score and does not change any format score. Per-format scoring belongs to later Q6 checkpoints.

## 9. Remaining risks and manual acceptance

The native Windows UI test could not be completed in this Codex session because the Windows computer-use helper failed twice with `registered Core setup is not complete for the installed app`. Automated Qt drag events passed, but a real Explorer-to-application gesture should still be checked on the target machine:

1. Start the application with the selector at TXT.
2. Drag one PDF from Windows Explorer onto the Add documents panel.
3. Confirm the selector changes to PDF, the filename appears once, status is Pending, and conversion does not start automatically.
4. Repeat with DOCX, PPTX, XLSX, CSV, TXT, JSON, XML, HTML, and HTM, including uppercase, spaces, and Unicode names.
5. Drop two files of the same type and confirm both appear.
6. Drop mixed supported types and confirm neither is added.
7. Drop an unsupported file and a folder and confirm they are rejected clearly.
8. Use Choose files afterward and confirm the selector still filters the dialog.

Potential platform differences in shell URL payloads remain until that checklist passes on supported Windows versions.

## 10. Next action

Proceed with Q6 shared quality policies: output validation, table representation selection, debug-metadata separation, and conversion-profile contracts. Then audit PDF and the other formats before assigning evidence-based per-format scores. Q7 remains reserved for installer and release work.
