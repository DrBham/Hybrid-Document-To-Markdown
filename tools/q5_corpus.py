"""Synthetic source fixtures and explicit source-derived semantic oracles for Q5."""
import base64
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

FORMATS = ("txt", "csv", "json", "xml", "html", "htm", "docx", "pptx", "xlsx", "pdf")
GOLDEN = Path(__file__).resolve().parents[1] / "tests/fixtures/q5/golden.json"


def make_pdf(path, pages):
    """Author a small vector PDF without a new fixture-generation dependency."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for commands in pages:
        page_id = len(objects) + 1
        kids.append(f"{page_id} 0 R")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id+1} 0 R >>".encode())
        stream = commands.encode("ascii")
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode()
    content, offsets = bytearray(b"%PDF-1.4\n"), []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(content)
    content.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        content.extend(f"{offset:010d} 00000 n \n".encode())
    content.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    path.write_bytes(content)


def build(root, case):
    from document_converter.core.options import ConversionOptions
    stress = case.startswith("stress-")
    extension = case.removeprefix("stress-")
    source = root / ("fixture." + extension)
    options = ConversionOptions(pdf_mode="text", pdf_columns=2 if not stress else 1)
    oracle = json.loads(GOLDEN.read_text(encoding="utf-8")).get(extension, {}).copy()
    image = None
    if extension in {"html", "htm", "docx", "pptx", "xlsx"} and not stress:
        from PIL import Image
        image = root / "diagram.png"
        Image.new("RGB", (16, 12), (38, 47, 56)).save(image)
    if extension in {"txt", "csv", "json", "xml", "html", "htm"}:
        content = oracle["source"]
        if stress:
            content = ("ID 日本語 café 00123  \n" * 100_000 + "END\n" if extension == "txt" else
                       "id;value;note\n" + "00123;1.2300;data\n" * 20_000)
        source.write_bytes(content.encode("utf-8"))
        if extension == "txt":
            oracle["exact"] = content
        if extension in {"json", "xml"}:
            # These fixed golden strings are hand-authored, not snapshots of conversion.
            oracle["exact"] = oracle["markdown"]
        if stress and extension == "csv":
            oracle = {"row": "| 00123 | 1.2300 | data |", "row_count": 20_000, "raw": content}
    elif extension == "docx":
        from docx import Document
        document = Document()
        document.add_heading("Network café", 1)
        document.add_paragraph("Start 日本語")
        document.add_paragraph("Router", style="List Bullet")
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).merge(table.cell(0, 1)).text = "Inventory"
        table.cell(1, 0).text = "00123"
        table.cell(1, 1).text = "1.2300"
        document.add_picture(str(image))
        document.add_paragraph("Figure 1: topology")
        document.add_paragraph("End")
        document.save(source)
    elif extension == "pptx":
        from pptx import Presentation
        from pptx.util import Inches
        document = Presentation()
        first = document.slides.add_slide(document.slide_layouts[5])
        first.shapes.title.text = "Network café"
        table = first.shapes.add_table(2, 2, Inches(1), Inches(1), Inches(4), Inches(1)).table
        for cell, value in zip([c for r in table.rows for c in r.cells], ["ID", "Value", "00123", "1.2300"]):
            cell.text = value
        first.shapes.add_picture(str(image), Inches(1), Inches(3))
        first.notes_slide.notes_text_frame.text = "Speaker 日本語"
        document.slides.add_slide(document.slide_layouts[5]).shapes.title.text = "Second slide"
        document.save(source)
    elif extension == "xlsx":
        from openpyxl import Workbook
        document = Workbook()
        sheet = document.active
        sheet.title = "Inventory"
        sheet.append(["ID", "Value", "Formula"])
        for _ in range(5000 if stress else 1):
            sheet.append(["00123", "1.2300", "=1+2"])
        if stress:
            oracle = {"row": "| 00123 | 1.2300 | =1+2 |", "row_count": 5000}
        else:
            from openpyxl.drawing.image import Image
            sheet.merge_cells("A4:B4")
            sheet["A4"] = "Merged 日本語"
            sheet.add_image(Image(str(image)), "D5")
            document.create_sheet("Second").append(["End"])
        document.save(source)
        document.close()
    elif extension == "pdf":
        if stress:
            make_pdf(source, [f"BT /F1 12 Tf 30 750 Td (PAGE {n:03d}) Tj ET" for n in range(1, 31)])
            oracle = {"ordered": [f"PAGE {n:03d}" for n in range(1, 31)], "pages": 30}
        else:
            make_pdf(source, ["BT /F1 12 Tf 30 750 Td (LEFT FIRST) Tj ET\nBT /F1 12 Tf 330 750 Td (RIGHT FIRST) Tj ET\nBT /F1 12 Tf 30 720 Td (LEFT SECOND) Tj ET\nBT /F1 12 Tf 330 720 Td (RIGHT SECOND) Tj ET"])
    if image is not None:
        oracle["image_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
    return source, options, oracle


def check(result, oracle, root):
    from document_converter.services.asset_package import AssetPackageExporter
    markdown = result.markdown
    checks = {}
    if "exact" in oracle:
        checks["exact_decoded_text"] = markdown == oracle["exact"]
    for i, fragment in enumerate(oracle.get("contains", [])):
        checks[f"source_fragment_{i}"] = fragment in markdown
    for i, fragment in enumerate(oracle.get("absent", [])):
        checks[f"forbidden_fragment_{i}"] = fragment not in markdown
    ordered = oracle.get("ordered", [])
    if ordered:
        positions = [markdown.find(value) for value in ordered]
        checks["source_order"] = all(p >= 0 for p in positions) and positions == sorted(set(positions))
    if "row" in oracle:
        checks["table_rows"] = markdown.splitlines().count(oracle["row"]) == oracle["row_count"]
    if "raw" in oracle:
        checks["raw_csv"] = oracle["raw"] in markdown
    if "pages" in oracle:
        checks["page_count"] = len(re.findall(r"^## Page \d+", markdown, re.M)) == oracle["pages"]
    if "image_sha256" in oracle:
        payloads = re.findall(r"data:image/[\w.+-]+;base64,([A-Za-z0-9+/=]+)", markdown)
        hashes = {hashlib.sha256(base64.b64decode(p, validate=True)).hexdigest() for p in payloads}
        checks["original_image_bytes"] = hashes == {oracle["image_sha256"]}
        package = root / "package.zip"
        AssetPackageExporter().export(markdown, package)
        with ZipFile(package) as archive:
            packaged = archive.read("document.md").decode("utf-8")
            references = set(re.findall(r"assets/[a-f0-9]+\.[a-z]+", packaged))
            checks["portable_asset_references"] = bool(references) and references <= set(archive.namelist())
            checks["packaged_image_bytes"] = {hashlib.sha256(archive.read(p)).hexdigest() for p in references} == hashes
    checks["no_internal_placeholders"] = not re.search(r"(?:HYBRIDIMAGE|HYBRIDPAGE|PRESERVEDTABLE)[A-F0-9]{32}", markdown)
    return checks
