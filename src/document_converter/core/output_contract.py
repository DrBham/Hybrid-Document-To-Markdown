"""Shared validation applied to every converter result."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re

from .models import ConversionResult


_INTERNAL_PLACEHOLDER = re.compile(
    r"(?:HYBRIDIMAGE|HYBRIDPAGE|PRESERVEDTABLE|PRESERVED|"
    r"OFFICEBLOCK|OFFICEREFERENCE)[A-F0-9]{32}"
)


def finalize_result(
    source: Path,
    result: ConversionResult,
    *,
    max_output_bytes: int,
) -> ConversionResult:
    """Validate and canonicalize the public result contract.

    Converters may use private placeholders while building Markdown, but none
    may escape through the router.  Source identity and format are verified so
    a parser cannot silently return a result for a different document type.
    """

    if not isinstance(result, ConversionResult):
        raise TypeError("Converter must return ConversionResult")

    source = Path(source)
    expected_format = source.suffix.lower().lstrip(".")
    if Path(result.source_path).resolve() != source.resolve():
        raise ValueError("Converter returned a different source_path")
    if result.source_format.lower().lstrip(".") != expected_format:
        raise ValueError("Converter returned a mismatched source_format")
    if not isinstance(result.markdown, str):
        raise TypeError("Converter markdown must be text")
    if "\x00" in result.markdown:
        raise ValueError("Markdown contains a NUL character")
    if _INTERNAL_PLACEHOLDER.search(result.markdown):
        raise ValueError("Markdown contains an unresolved internal placeholder")

    try:
        encoded = result.markdown.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Markdown is not valid UTF-8 text") from exc
    if len(encoded) > max_output_bytes:
        raise ValueError("Markdown exceeds max_output_bytes")

    warnings: list[str] = []
    for warning in result.warnings:
        if not isinstance(warning, str):
            raise TypeError("Converter warnings must be text")
        normalized = " ".join(warning.split())
        if normalized and normalized not in warnings:
            warnings.append(normalized)

    return replace(
        result,
        source_path=source,
        source_format=expected_format,
        warnings=tuple(warnings),
    )
