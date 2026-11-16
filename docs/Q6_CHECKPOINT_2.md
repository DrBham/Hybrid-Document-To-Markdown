# Q6 Checkpoint 2 — Shared output policy and all-format audit

Completed on 2026-11-17 for Q6-B. The complete suite passes: **242 tests in 33.46 seconds**. The unchanged source-authored corpus passes **101/101 semantic, media, portability, offline, process, and stress checks** across ten formats and four stress cases.

## Scope

Q6-B combines the format audit into three families instead of creating a separate phase for every extension:

| Family | Formats | Verified contract |
|---|---|---|
| Text and structured data | TXT, CSV, JSON, XML | Exact decoded content where applicable, fenced structured source, CSV table plus recoverable original source, Unicode and numeric strings |
| Web and Office | HTML, HTM, DOCX, PPTX, XLSX | Source order, semantic tables, notes, local media bytes, portable assets, formulas/cell values, and source-backed structure metadata |
| Page layout | PDF | Page order, column policy, table geometry, bounded pages, and explicit warnings for reading-order/OCR limitations |

## Shared output contract

Every result now passes one router-level contract before it reaches batch conversion, preview, or export:

- the converter must return `ConversionResult`;
- `source_path` and `source_format` must match the requested file;
- Markdown must be UTF-8 encodable and contain no NUL character;
- private conversion placeholders must not escape into public output;
- warnings are whitespace-normalized, empty warnings removed, and duplicates removed;
- the configured output-size budget is enforced in the same finalization path.

This closes a gap where each converter previously relied on its own implicit output assumptions.

## Structured metadata policy

XLSX cell records, PDF table geometry, and PPTX source structure remain inside the generated Markdown by default. They are now wrapped in explicit `hybrid-metadata` boundaries and collapsible `<details>` blocks so applications can distinguish readable content from source-evidence appendices without losing that evidence.

`ConversionOptions(metadata_mode="omit")` removes those diagnostic appendices while retaining the readable document content. The GUI and default API continue to use `embedded`, preserving the existing fidelity-first behavior.

## Evidence

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
# 242 passed in 33.46s

.\.venv\Scripts\python.exe tools\evaluate_q5.py --output docs\benchmarks\q6-windows.json
# passed: true; 101/101 checks across 14 cases
```

The Q5 corpus was intentionally reused unchanged so Q6-B could not weaken or rewrite its own acceptance oracle. Twenty Q6-B regression cases add the shared output contract, metadata modes, unsafe-output rejection, warning canonicalization, and a direct ten-format gate.

The recorded environment is Windows 11 with Python 3.13. The generated evidence is stored in `docs/benchmarks/q6-windows.json`.

## Results and limits

All defined gates pass. This demonstrates the documented contracts for generated fixtures; it is **not** a general accuracy percentage for arbitrary real-world documents. Remaining known limits still apply: no OCR, no inferred diagram meaning, PDF reading order depends on geometry, complex renderer support varies, formula caches may be stale, and external clients may handle Base64 differently.

Q6-B is complete. Q6-C owns the final repository audit, clean full-workflow acceptance, remaining reproducible fixes, documentation consistency, and the final go/no-go gate before Q7 installer work.
