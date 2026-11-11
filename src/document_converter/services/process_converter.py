"""Disposable parser processes with cancellation, deadline and private scratch files."""
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic

from ..core.models import ConversionResult
from ..core.options import ConversionOptions


class ConversionCancelled(RuntimeError):
    pass


class ConversionTimedOut(TimeoutError):
    pass


class ConversionProcessError(RuntimeError):
    pass


class ProcessConverter:
    """Run built-in converters without allowing a hung parser to hold the GUI.

    The deadline includes Python startup and imports. It is not a RAM limit.
    A separate process per file deliberately trades startup time for isolation.
    """

    def __init__(self, options=None, *, timeout_seconds=120.0, scratch_root=None):
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        self.options = options or ConversionOptions()
        self.timeout_seconds = timeout_seconds
        self.scratch_root = scratch_root

    def _command(self, request):
        return [sys.executable, "-m", "document_converter.services.conversion_worker", str(request)]

    def convert(self, source: Path, *, cancelled: Event | None = None):
        cancelled = cancelled if cancelled is not None else Event()
        if cancelled.is_set():
            raise ConversionCancelled("Cancelled before conversion")
        with TemporaryDirectory(prefix="hybrid-worker-", dir=self.scratch_root) as folder:
            root = Path(folder)
            request = root / "request.json"
            request.write_text(json.dumps({"source": str(source.resolve()),
                                          "options": asdict(self.options)}), encoding="utf-8")
            env = os.environ.copy()
            source_root = str(Path(__file__).resolve().parents[2])
            env["PYTHONPATH"] = source_root + os.pathsep + env.get("PYTHONPATH", "")
            # Any parser-owned temporary files remain inside the parent's cleanup scope.
            env.update(TMP=str(root), TEMP=str(root), TMPDIR=str(root))
            start = monotonic()
            process = subprocess.Popen(
                self._command(request), env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                while process.poll() is None:
                    if cancelled.wait(0.05):
                        raise ConversionCancelled("Cancelled during conversion")
                    if monotonic() - start >= self.timeout_seconds:
                        raise ConversionTimedOut(f"Conversion exceeded {self.timeout_seconds:g} seconds")
                if cancelled.is_set():
                    raise ConversionCancelled("Cancelled during conversion")
                if process.returncode != 0:
                    raise ConversionProcessError(f"Parser process exited with code {process.returncode}")
                response = root / "response.json"
                if not response.exists() or response.stat().st_size > 1024 * 1024:
                    raise ConversionProcessError("Parser returned missing or oversized metadata")
                metadata = json.loads(response.read_text(encoding="utf-8"))
                if "error" in metadata:
                    raise ConversionProcessError(metadata["error"])
                output = root / "document.md"
                if not output.exists() or output.stat().st_size > self.options.max_output_bytes:
                    raise ConversionProcessError("Parser returned missing or oversized Markdown")
                markdown = output.read_bytes().decode("utf-8")
                return ConversionResult(source, metadata["source_format"], markdown,
                                        tuple(metadata["warnings"]))
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

