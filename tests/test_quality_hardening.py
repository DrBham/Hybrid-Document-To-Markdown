import base64
import json
import os
import re
import socket
from zipfile import ZipFile

import pytest
from openpyxl import Workbook
from PIL import Image

from document_converter.core.options import ConversionOptions
from document_converter.core.router import ConverterRouter
from document_converter.core.serialization import fenced
from document_converter.services.asset_package import AssetPackageExporter
from document_converter.services.markdown_exporter import MarkdownExporter
from document_converter.services.batch_converter import BatchConverter
from document_converter.embedded_media.extractor import DocumentImageExtractor


@pytest.mark.parametrize("text", ["", "\t  \r\nline  \n\n\n", "日本語 — α\n", "```python\npass\n```", "  "])
def test_txt_exact_content(tmp_path, text):
    source = tmp_path / "source.txt"
    source.write_bytes(text.encode("utf-8"))
    assert ConverterRouter().convert(source).markdown == text


@pytest.mark.parametrize("extension,text", [
    ("json", '{"n":1.2300,"large":9007199254740993,"text":"````"}'),
    ("xml", '<!DOCTYPE root [<!ENTITY ext SYSTEM "file:///private">]><root>&ext;</root>'),
])
def test_structured_data_fence_preserves_source_without_entity_resolution(tmp_path, extension, text):
    source = tmp_path / f"source.{extension}"
    source.write_text(text, encoding="utf-8")
    markdown = ConverterRouter().convert(source).markdown
    assert markdown == fenced(text, extension)
    assert markdown.splitlines()[0].startswith("`" * (5 if extension == "json" else 3))


def test_csv_preserves_original_and_multiline(tmp_path):
    source = tmp_path / "source.csv"
    original = 'id;note\r\n00123;"a|b\nnext"\r\n'
    source.write_bytes(original.encode())
    result = ConverterRouter().convert(source)
    assert "| 00123 | a\\|b<br>next |" in result.markdown
    assert original in result.markdown


def test_xlsx_preserves_cells_formula_merge_and_sheet_order(tmp_path):
    source = tmp_path / "source.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "First"
    sheet.append(["id", "amount", "formula"])
    sheet.append(["00123", "9007199254740993", "=1+2"])
    sheet.merge_cells("A4:B4")
    workbook.create_sheet("Second").append(["data"])
    workbook.save(source)
    result = ConverterRouter().convert(source)
    assert "| 00123 | 9007199254740993 | =1+2 |" in result.markdown
    records = json.loads(re.search(r"```json\n(.*?)\n```", result.markdown, re.S).group(1))
    assert records["merged_ranges"] == ["A4:B4"]
    formula = next(c for c in records["cells"] if c["cell"] == "C2")
    assert formula["value"] == "=1+2" and formula["cached_value"] is None
    assert result.markdown.index("## First") < result.markdown.index("## Second")
    assert result.warnings


def test_atomic_replace_failure_retains_original_and_cleans_temp(tmp_path, monkeypatch):
    target = tmp_path / "result.md"
    target.write_text("original", encoding="utf-8")
    def fail(*args):
        raise OSError("simulated replace failure")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        MarkdownExporter().export("replacement", target, overwrite=True)
    assert target.read_text() == "original"
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_publish_race_preserves_other_writer(tmp_path, monkeypatch):
    target = tmp_path / "result.md"
    def race(source, destination):
        destination.write_text("other writer")
        raise FileExistsError(destination)
    monkeypatch.setattr(os, "link", race)
    with pytest.raises(FileExistsError):
        MarkdownExporter().export("new", target)
    assert target.read_text() == "other writer"
    assert list(tmp_path.iterdir()) == [target]


def test_zip_asset_package_roundtrip_deduplicates(tmp_path):
    data = b"original bytes"
    uri = "data:image/png;base64," + base64.b64encode(data).decode()
    target = tmp_path / "package.zip"
    AssetPackageExporter().export(f"![one]({uri})\n![two]({uri})", target)
    with ZipFile(target) as archive:
        assets = [name for name in archive.namelist() if name.startswith("assets/")]
        assert len(assets) == 1
        assert archive.read(assets[0]) == data
        assert archive.read("document.md").decode().count(assets[0]) == 2
    with pytest.raises(FileExistsError):
        AssetPackageExporter().export("new", target)


def test_archive_budget_prevents_parser_invocation(tmp_path):
    source = tmp_path / "source.docx"
    with ZipFile(source, "w") as archive:
        archive.writestr("word/document.xml", "x" * 200)
    with pytest.raises(ValueError, match="max_uncompressed_bytes"):
        ConverterRouter(options=ConversionOptions(max_uncompressed_bytes=100)).convert(source)


def test_output_budget_rejects_without_truncation(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("1234567890")
    with pytest.raises(ValueError, match="max_output_bytes"):
        ConverterRouter(options=ConversionOptions(max_output_bytes=5)).convert(source)


def test_html_pre_and_local_image_work_without_network(tmp_path, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network forbidden")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    image = tmp_path / "chart.png"
    Image.new("RGB", (8, 8), "red").save(image)
    source = tmp_path / "source.html"
    source.write_bytes(b'<h1>Title</h1><pre>  x  \n\n\n y</pre><img src="chart.png"><script>alert(1)</script>')
    result = ConverterRouter().convert(source)
    assert "  x  \n\n\n y" in result.markdown
    assert "alert" not in result.markdown
    payload = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", result.markdown)
    assert payload and base64.b64decode(payload.group(1)) == image.read_bytes()


def test_html_blocks_asset_outside_document_root(tmp_path):
    image = tmp_path / "private.png"
    Image.new("RGB", (8, 8)).save(image)
    folder = tmp_path / "public"
    folder.mkdir()
    source = folder / "source.html"
    source.write_text('<img src="../private.png">')
    result = ConverterRouter().convert(source)
    assert "base64" not in result.markdown
    assert result.warnings


@pytest.mark.parametrize("mode", ["pages", "images", "text"])
def test_pdf_modes(tmp_path, mode):
    source = tmp_path / "source.pdf"
    Image.new("RGB", (16, 12), "red").save(source, format="PDF")
    result = ConverterRouter(options=ConversionOptions(pdf_mode=mode)).convert(source)
    assert ("data:image/" in result.markdown) == (mode != "text")
    assert any("text layer" in warning for warning in result.warnings)


def test_pdf_pixel_budget(tmp_path):
    source = tmp_path / "source.pdf"
    Image.new("RGB", (16, 12)).save(source, format="PDF")
    extractor = DocumentImageExtractor(options=ConversionOptions(max_page_pixels=10))
    with pytest.raises(ValueError, match="max_page_pixels"):
        extractor.extract(source, tmp_path / "images")


def test_cancel_remaining_files_and_restart(tmp_path):
    first, second = tmp_path / "first.txt", tmp_path / "second.txt"
    first.write_text("first")
    second.write_text("second")
    batch = BatchConverter()
    batch.cancel()
    assert len(batch.convert([first, second]).failed) == 2
    batch.reset_cancellation()
    assert len(batch.convert([first, second]).successful) == 2


def test_docx_semantic_order_and_media_provenance(tmp_path):
    from docx import Document
    source = tmp_path / "source.docx"
    image = tmp_path / "chart.png"
    Image.new("RGB", (8, 8), "blue").save(image)
    document = Document()
    document.add_heading("Overview", 1)
    document.add_paragraph("Paragraph before table")
    table = document.add_table(rows=2, cols=2)
    for cell, text in zip([c for r in table.rows for c in r.cells], ["ID", "Value", "00123", "1.2300"]):
        cell.text = text
    document.add_paragraph("Paragraph after table")
    document.add_picture(str(image))
    document.save(source)
    result = ConverterRouter().convert(source)
    assert result.markdown.index("# Overview") < result.markdown.index("Paragraph before table") < result.markdown.index("00123") < result.markdown.index("Paragraph after table")
    assert "word/document.xml" in result.markdown


def test_pptx_slide_order_table_and_notes(tmp_path):
    from pptx import Presentation
    from pptx.util import Inches
    source = tmp_path / "source.pptx"
    presentation = Presentation()
    for title in ["First slide", "Second slide"]:
        slide = presentation.slides.add_slide(presentation.slide_layouts[5])
        slide.shapes.title.text = title
    first = presentation.slides[0]
    first.notes_slide.notes_text_frame.text = "Speaker instruction"
    table = first.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(5), Inches(1)).table
    for cell, text in zip([c for r in table.rows for c in r.cells], ["ID", "Value", "00123", "1.2300"]):
        cell.text = text
    presentation.save(source)
    result = ConverterRouter().convert(source)
    assert result.markdown.index("First slide") < result.markdown.index("00123") < result.markdown.index("Second slide")
    assert "Speaker instruction" in result.markdown


def test_workbook_cached_view_keeps_formula_metadata(tmp_path):
    source = tmp_path / "source.xlsx"
    workbook = Workbook()
    workbook.active.title = "Chosen"
    workbook.active.append(["=1+2"])
    workbook.create_sheet("Excluded").append(["private sheet value"])
    workbook.save(source)
    result = ConverterRouter(options=ConversionOptions(spreadsheet_view="cached", sheets=("Chosen",))).convert(source)
    assert "&#91;cache unavailable&#93;" in result.markdown
    assert "=1+2" in result.markdown
    assert "private sheet value" not in result.markdown


def test_pdf_page_budget_before_text_parser(tmp_path):
    source = tmp_path / "source.pdf"
    first = Image.new("RGB", (8, 8))
    first.save(source, format="PDF", save_all=True, append_images=[Image.new("RGB", (8, 8))])
    with pytest.raises(ValueError, match="max_pdf_pages"):
        ConverterRouter(options=ConversionOptions(max_pdf_pages=1)).convert(source)


def test_invalid_encoding_fails_without_dropping_bytes(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"caf\xe9")
    with pytest.raises(UnicodeDecodeError):
        ConverterRouter().convert(source)
    assert ConverterRouter(options=ConversionOptions(encoding="cp1252")).convert(source).markdown == "caf\xe9"
