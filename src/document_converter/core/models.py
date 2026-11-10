
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConversionResult:
    """Represent the result of a document conversion."""

    source_path: Path
    source_format: str
    markdown: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileConversionOutcome:
    """Represent either a successful conversion or a per-file failure."""

    source_path: Path
    result: ConversionResult | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        has_result = self.result is not None
        has_error = self.error is not None

        if has_result == has_error:
            raise ValueError(
                "An outcome must contain either a result or an error"
            )

    @property
    def succeeded(self) -> bool:
        """Return whether this file converted successfully."""

        return self.result is not None


@dataclass(frozen=True)
class BatchConversionResult:
    """Collect independent outcomes from one same-extension batch."""

    extension: str
    outcomes: tuple[FileConversionOutcome, ...]

    @property
    def successful(self) -> tuple[FileConversionOutcome, ...]:
        """Return successful file outcomes."""

        return tuple(outcome for outcome in self.outcomes if outcome.succeeded)

    @property
    def failed(self) -> tuple[FileConversionOutcome, ...]:
        """Return failed file outcomes."""

        return tuple(outcome for outcome in self.outcomes if not outcome.succeeded)
