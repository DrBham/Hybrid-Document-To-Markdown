"""Print synthetic fidelity probes; this is a diagnostic, not an accuracy score.

Run from the repository root with the project virtual environment. No private
documents are read. Temporary fixtures are removed after conversion.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openpyxl import Workbook

from document_converter.core.router import ConverterRouter


SAMPLES = {
    "spaces.txt": "line with hard break  \nnext\n\n\n    code\t  \n\n",
    "data.json": '{"id":"00123","value":1.2300,"nested":{"x":null}}\n',
    "data.xml": '<root xmlns="urn:test" id="00123"><![CDATA[a < b]]>'
    '<!--note--><x>  text  </x></root>\n',
    "comma.csv": 'id,precise,note\n00123,1.2300,"a|b"\n'
    '00007,9007199254740993,"line1\nline2"\n',
    "semicolon.csv": "id;note\n00123;hello\n",
    "relative.html": '<h1>Title</h1><pre>  x  \n\n\n  y</pre>'
    '<img src="images/chart.png" alt="Chart">'
    '<a href="guide.html">Guide</a>',
}


def main() -> None:
    router = ConverterRouter()
    observations = []
    with TemporaryDirectory(prefix="hybrid-quality-audit-") as temporary:
        directory = Path(temporary)
        for name, source_text in SAMPLES.items():
            source = directory / name
            source.write_bytes(source_text.encode("utf-8"))
            observations.append({
                "fixture": name,
                "source_text": source_text,
                "markdown": router.convert(source).markdown,
            })

        source = directory / "numbers.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        rows = [
            ["id", "amount", "formula"],
            ["00123", "1.2300", "=1+2"],
            ["00007", "9007199254740993", "=2+2"],
        ]
        for row in rows:
            sheet.append(row)
        workbook.save(source)
        workbook.close()
        observations.append({
            "fixture": source.name,
            "source_rows": rows,
            "markdown": router.convert(source).markdown,
        })

    print(json.dumps(observations, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
