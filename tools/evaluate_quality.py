"""Reproducible synthetic corpus, isolated timing and process peak memory.

Prints JSON to stdout. Each format runs in a fresh process; memory includes
Python, imported dependencies, fixture creation, and conversion (native too).
These are smoke/fidelity oracles, not a general document accuracy score.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def peak_memory():
    if os.name != "nt":
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("peak", "working", "peak_pool", "pool", "peak_nonpool", "nonpool", "pagefile", "peak_pagefile")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.peak


def evaluate(extension):
    from document_converter.core.router import ConverterRouter
    from PIL import Image
    with TemporaryDirectory(prefix="hybrid-corpus-") as temporary:
        source = Path(temporary) / ("fixture." + extension)
        marker = "00123"
        expected = None
        if extension == "docx":
            from docx import Document
            doc = Document()
            doc.add_heading("Corpus", 1)
            doc.add_paragraph(marker)
            doc.save(source)
        elif extension == "pptx":
            from pptx import Presentation
            doc = Presentation()
            doc.slides.add_slide(doc.slide_layouts[5]).shapes.title.text = marker
            doc.save(source)
        elif extension == "xlsx":
            from openpyxl import Workbook
            doc = Workbook()
            doc.active.append(["ID", "Formula"])
            doc.active.append([marker, "=1+2"])
            doc.save(source)
        elif extension == "pdf":
            Image.new("RGB", (32, 24), "blue").save(source, format="PDF")
            marker = "data:image/png;base64,"
        else:
            content = {"txt": "00123  \n\n\n\tend  ", "csv": 'id;note\n00123;"line1\nline2"\n',
                       "json": '{"id":"00123","number":1.2300}',
                       "xml": '<root id="00123"><![CDATA[a < b]]></root>',
                       "html": '<h1>00123</h1><pre>  code  \n\n\nend</pre>',
                       "htm": '<h1>00123</h1><p>Paragraph</p>'}[extension]
            source.write_bytes(content.encode())
            if extension == "txt":
                expected = content
        router = ConverterRouter()
        start = perf_counter()
        result = router.convert(source)
        seconds = perf_counter() - start
        checks = {"expected_content_present": marker in result.markdown}
        if expected is not None:
            checks["exact_source_text"] = result.markdown == expected
        if extension == "xlsx":
            checks["formula_preserved"] = "=1+2" in result.markdown
        if extension == "csv":
            checks["multiline_preserved"] = "line1<br>line2" in result.markdown
        return {"format": extension, "checks": checks, "input_bytes": source.stat().st_size,
                "output_utf8_bytes": len(result.markdown.encode()), "seconds": round(seconds, 6),
                "process_peak_bytes": peak_memory(), "warnings": list(result.warnings)}


if __name__ == "__main__":
    if len(sys.argv) == 2:
        print(json.dumps(evaluate(sys.argv[1])))
    else:
        rows = []
        for extension in ("txt", "csv", "json", "xml", "html", "htm", "docx", "pptx", "xlsx", "pdf"):
            completed = subprocess.run([sys.executable, __file__, extension], capture_output=True, text=True, check=True, timeout=120)
            rows.append(json.loads(completed.stdout))
        print(json.dumps({"python": sys.version.split()[0], "platform": sys.platform,
                          "method": "one synthetic fixture per format; one fresh process each; no accuracy percentage", "results": rows}, indent=2))
