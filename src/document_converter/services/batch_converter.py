"""Same-extension batch conversion service."""

from collections.abc import Iterable
from pathlib import Path
from threading import Event

from ..core.models import (
    BatchConversionResult,
    FileConversionOutcome,
)
from ..core.router import ConverterRouter
from .process_converter import ProcessConverter


class BatchConverter:
    """Convert files independently while preserving per-file outcomes."""

    def __init__(self, router: ConverterRouter | None = None, *, options=None,
                 timeout_seconds=120.0):
        if router is not None and options is not None:
            raise ValueError("Pass either a custom router or options, not both")
        self._router = router
        self._process = ProcessConverter(options, timeout_seconds=timeout_seconds) if router is None else None
        self._cancelled = Event()

    def cancel(self) -> None:
        """Stop the active built-in parser process and cancel remaining files.

        Injected custom routers retain cooperative cancellation between files.
        """
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
                result = (self._process.convert(path, cancelled=self._cancelled)
                          if self._process is not None else self._router.convert(path))
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
