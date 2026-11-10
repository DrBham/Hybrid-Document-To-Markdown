"""Same-extension batch conversion service."""

from collections.abc import Iterable
from pathlib import Path
from threading import Event

from ..core.models import (
    BatchConversionResult,
    FileConversionOutcome,
)
from ..core.router import ConverterRouter


class BatchConverter:
    """Convert files independently while preserving per-file outcomes."""

    def __init__(self, router: ConverterRouter | None = None):
        self._router = router if router is not None else ConverterRouter()
        self._cancelled = Event()

    def cancel(self) -> None:
        """Stop before the next file; never kill a parser thread mid-write."""
        self._cancelled.set()

    def reset_cancellation(self) -> None:
        self._cancelled.clear()

    def convert(self, file_paths: Iterable[Path]) -> BatchConversionResult:
        """Convert a non-empty batch whose extensions all match."""

        paths = tuple(Path(path) for path in file_paths)

        if not paths:
            raise ValueError("Batch must contain at least one file")

        extensions = {path.suffix.lower() for path in paths}

        if len(extensions) != 1:
            raise ValueError(
                "All files in a batch must use the same extension"
            )

        extension = extensions.pop()
        outcomes: list[FileConversionOutcome] = []

        for path in paths:
            if self._cancelled.is_set():
                outcomes.append(FileConversionOutcome(source_path=path, error="Cancelled before conversion"))
                continue
            try:
                result = self._router.convert(path)
            except Exception as exc:
                outcomes.append(
                    FileConversionOutcome(
                        source_path=path,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
            else:
                outcomes.append(
                    FileConversionOutcome(
                        source_path=path,
                        result=result,
                    )
                )

        return BatchConversionResult(
            extension=extension,
            outcomes=tuple(outcomes),
        )
