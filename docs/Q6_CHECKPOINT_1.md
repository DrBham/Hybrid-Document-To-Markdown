# Q6 Checkpoint 1 — Drag-and-drop P0

Updated on 2026-11-17 after reviewing the supplied Windows screen recording. The full suite passes: **222 tests in 32.82 seconds**. Q6 remains in progress because native Explorer re-acceptance, shared output policies, format-quality improvements, and per-format scoring remain.

## 1. Objective

Restore dependable drag-and-drop without changing the same-extension batch model or breaking Browse/Select File. A dropped file should be recognized from its own extension even when the GUI starts with the TXT selector.

## 2. Root cause

The first defect was filter routing: `DropZone.dropEvent()` emitted valid local paths into the same selector-filtered path used by Browse, so a PDF dropped while the selector was `.txt` was rejected. The supplied recording then exposed a second defect: only the `DropZone` frame accepted native drops. Windows therefore displayed the forbidden cursor when the file crossed the selected-files panel and other child widgets. Changing the selector to PDF could not solve that target-coverage problem.

Affected code: `src/document_converter/gui/main_window.py`, especially `DropZone` and `MainWindow.add_files()`. Severity: P0 because the primary direct-manipulation workflow appeared nonfunctional. Regression risk: batch type selection and Browse filtering.

## 3. Implementation

- Browse keeps its explicit selector filter.
- Drop extracts decoded local paths from Qt URL payloads and checks that an existing file has a supported extension.
- A new dropped-file route detects the single supported extension, updates the selector, then reuses the established `add_files()` validation and list updates.
- Same-type multiple files are accepted. Mixed supported formats are rejected before any list state changes. Unsupported or missing entries are skipped and reported when a valid same-type batch remains.
- Drag enter and drag move provide acceptance feedback only for supported local files. Drop never starts conversion automatically.
- `MainWindow` is also a drop target and routes supported files from the selected-files panel, preview, or other application surfaces through the same validation flow.
- GUI help and accessibility text explain that the selector filters Browse while Drop detects type automatically.

No dependency, converter behavior, document output, or export policy changed.

## 4. Modified files

| File | Change |
|---|---|
| `src/document_converter/gui/main_window.py` | URL parsing, drag-enter/move/drop validation, automatic dropped-type selection, mixed-format handling, and help text |
| `tests/test_gui.py` | Seventeen Q6 cases, including ten extension parameters, full-window routing, and Browse regression |
| `README.md`, `CHANGELOG.md`, quality reports | Q6 status, evidence, limitations, and next checkpoint |

## 5. Tests performed

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gui.py -q -p no:cacheprovider
# 29 passed

.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
# 222 passed in 32.82s
```

The automated matrix covers TXT, DOCX, PDF, PPTX, XLSX, CSV, HTML, HTM, JSON, and XML; uppercase extensions; spaces; Unicode filenames; multiple same-type files; unsupported URLs; non-URL payloads; mixed supported formats; visual drag state; full-window routing; and the Browse path.

## 6. Before / after evidence

| Scenario | Before | After |
|---|---|---|
| Drop PDF while selector starts at TXT | Rejected as not matching `.TXT` | PDF is detected, selector changes to PDF, file becomes Pending |
| Drop same-type batch | Depended on manually matching selector | Extension detected once; valid files are added together |
| Drop mixed PDF and DOCX | Filter-dependent partial interpretation | Entire drop rejected with a one-format-per-batch message |
| Drop unsupported-only payload | Drag looked acceptable until drop | Drag enter is rejected; drop route also reports supported formats |
| Browse PDF with PDF filter | Existing behavior | Still adds the selected PDF |
| Drag over selected-files or another panel | Windows shows a forbidden cursor | Main window accepts and routes the file through the normal drop validation |

## 7. Regression status

The complete 222-test suite passes. Conversion workers, all format converters, preview, cancellation, Base64 media, ZIP export, and atomic Markdown export retain their existing tests. The selector continues to constrain Browse, and the file list continues to enforce one extension per batch.

## 8. Quality result

The automated P0 functional gate passes for all ten supported extensions. This is not a 90/100 conversion-quality score and does not change any format score. Per-format scoring belongs to later Q6 checkpoints.

## 9. Remaining risks and manual acceptance

The supplied recording was reviewed frame by frame and is valid failure evidence for the earlier build. The Windows computer-use helper could not launch the application in this Codex session because it failed twice with `registered Core setup is not complete for the installed app`. Automated Qt events now cover the newly identified full-window route, but the corrected build should still be rechecked with a real Explorer gesture:

1. Start the application with the selector at TXT.
2. Drag one PDF from Windows Explorer first onto the selected-files panel, then onto the Add documents panel.
3. Confirm the selector changes to PDF, the filename appears once, status is Pending, and conversion does not start automatically.
4. Repeat with DOCX, PPTX, XLSX, CSV, TXT, JSON, XML, HTML, and HTM, including uppercase, spaces, and Unicode names.
5. Drop two files of the same type and confirm both appear.
6. Drop mixed supported types and confirm neither is added.
7. Drop an unsupported file and a folder and confirm they are rejected clearly.
8. Use Choose files afterward and confirm the selector still filters the dialog.

Potential platform differences in shell URL payloads remain until that checklist passes on supported Windows versions.

## 10. Next action

Proceed with Q6 shared quality policies: output validation, table representation selection, debug-metadata separation, and conversion-profile contracts. Then audit PDF and the other formats before assigning evidence-based per-format scores. Q7 remains reserved for installer and release work.
