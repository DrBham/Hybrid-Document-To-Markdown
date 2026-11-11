"""Private child entry point; no GUI imports, networking, or final export writes."""
import json
from pathlib import Path
import sys

from .offline import install_network_guard


def main(request_path):
    install_network_guard()
    request_path = Path(request_path)
    root = request_path.parent
    request = json.loads(request_path.read_text(encoding="utf-8"))
    try:
        from ..core.options import ConversionOptions
        from ..core.router import ConverterRouter
        result = ConverterRouter(options=ConversionOptions(**request["options"])).convert(Path(request["source"]))
        (root / "document.md").write_bytes(result.markdown.encode("utf-8"))
        metadata = {"source_format": result.source_format, "warnings": result.warnings}
    except Exception as exc:
        # Parser exception strings may contain source text. Keep diagnostics generic.
        if isinstance(exc, ImportError):
            message = "Required parser dependency is unavailable; reinstall the project requirements."
        else:
            message = "Conversion failed; check file integrity, encoding, and configured resource limits."
        metadata = {"error": f"{type(exc).__name__}: {message}"}
    (root / "response.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
