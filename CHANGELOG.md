# Changelog

## Unreleased — Conversion quality audit

- Preserve converter output exactly in the embedded-media decorator, including trailing spaces, tabs, and blank lines. Add only the separator needed before the media appendix.
- Add 12 regression cases with and without embedded images; verify the complete decoded DOCX image bytes.
- Record architecture, reproducible fidelity findings, prioritized risks, quality metrics, and checkpoints Q1–Q6 in `docs/CONVERSION_QUALITY_AUDIT.md`.
- Add synthetic fidelity probes in `tools/audit_conversion_quality.py`.
- Update README status and limitations. Q1 is complete; Q2 is WIP. Release packaging follows quality hardening.
- Validation: 80 tests passed before the change; 92 passed afterwards. Upstream whitespace normalization and the documented XLSX/CSV issues remain unresolved.
