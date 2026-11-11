"""Source-order, portability and failure acceptance for contextual media."""
import base64
import hashlib
import os
import re
from zipfile import ZipFile

import pytest
from docx import Document
from openpyxl import Workbook
from openpyxl.drawing.image import Image as SheetImage
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

from document_converter.core.options import ConversionOptions
from document_converter.core.router import ConverterRouter
from document_converter.core.models import ConversionResult, InlineImage
from document_converter.embedded_media.converter import EmbeddedMediaDocumentConverter
from document_converter.services.asset_package import AssetPackageExporter


def picture(tmp_path, name="chart.png", color="navy"):
    path = tmp_path / name
    Image.new("RGB", (24, 16), color).save(path)
    return path


def definitions(markdown):
    return dict(re.findall(r"^\[([^\]]+)\]: (data:image/[^\n]+)$", markdown, re.M))


def assert_package_resolves(markdown, target):
    AssetPackageExporter().export(markdown, target)
    with ZipFile(target) as archive:
        text = archive.read("document.md").decode("utf-8")
        for asset in re.findall(r"assets/[a-f0-9]+\.[a-z]+", text):
            assert asset in archive.namelist()
            assert hashlib.sha256(archive.read(asset)).hexdigest() == asset.split("/")[1].split(".")[0]
        return text, {name: archive.read(name) for name in archive.namelist() if name.startswith("assets/")}


def test_word_occurrences_stay_with_captions_and_share_payload(tmp_path):
    image = picture(tmp_path)
    source = tmp_path / "report.docx"
    doc = Document()
    doc.add_paragraph("Before first")
    doc.add_picture(str(image))
    doc.add_paragraph("Figure 1: original caption", style="Caption")
    doc.add_paragraph("Between figures")
    doc.add_picture(str(image))
    doc.add_paragraph("Figure 2: second usage", style="Caption")
    doc.save(source)
    result = ConverterRouter().convert(source)
    refs = list(re.finditer(r"!\[[^\]]*\]\[hybrid-media-[^\]]+\]", result.markdown))
    assert len(refs) == 2
    assert result.markdown.index("Before first") < refs[0].start() < result.markdown.index("Figure 1")
    assert result.markdown.index("Between figures") < refs[1].start() < result.markdown.index("Figure 2")
    assert len(definitions(result.markdown)) == 1
    assert result.markdown.count("data:image/png;base64,") == 1
    assert "HYBRIDIMAGE" not in result.markdown
    _, assets = assert_package_resolves(result.markdown, tmp_path / "portable.zip")
    assert list(assets.values()) == [image.read_bytes()]


def test_word_table_image_is_exported_from_html_src(tmp_path):
    image = picture(tmp_path)
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1)).paragraphs[0].add_run().add_picture(str(image))
    source = tmp_path / "table.docx"
    doc.save(source)
    result = ConverterRouter().convert(source)
    assert '<img alt=' in result.markdown
    text, assets = assert_package_resolves(result.markdown, tmp_path / "table.zip")
    assert 'src="assets/' in text
    assert "data:image/" not in text
    assert list(assets.values()) == [image.read_bytes()]


def test_powerpoint_image_keeps_slide_and_caption_order(tmp_path):
    image = picture(tmp_path)
    source = tmp_path / "slides.pptx"
    presentation = Presentation()
    for title in ("First slide", "Second slide"):
        slide = presentation.slides.add_slide(presentation.slide_layouts[5])
        slide.shapes.title.text = title
        slide.shapes.add_picture(str(image), Inches(1), Inches(2))
        slide.shapes.add_textbox(Inches(1), Inches(4), Inches(5), Inches(1)).text = title + " caption"
    presentation.save(source)
    result = ConverterRouter().convert(source)
    refs = list(re.finditer(r"!\[[^\]]*\]\[hybrid-media-[^\]]+\]", result.markdown))
    assert len(refs) == 2
    assert result.markdown.index("First slide") < refs[0].start() < result.markdown.index("First slide caption")
    assert result.markdown.index("Second slide") < refs[1].start() < result.markdown.index("Second slide caption")
    assert len(definitions(result.markdown)) == 1
    assert "Picture1.jpg" not in result.markdown


@pytest.mark.parametrize("selected_has_image", [True, False])
def test_excel_sheet_selection_cannot_leak_other_images(tmp_path, selected_has_image):
    allowed = picture(tmp_path, "allowed.png", "navy")
    excluded = picture(tmp_path, "excluded.png", "red")
    book = Workbook()
    chosen = book.active
    chosen.title = "Chosen"
    chosen.append(["Data"])
    if selected_has_image:
        chosen.add_image(SheetImage(allowed), "D5")
    other = book.create_sheet("Excluded")
    other.add_image(SheetImage(excluded), "A1")
    source = tmp_path / "book.xlsx"
    book.save(source)
    result = ConverterRouter(options=ConversionOptions(sheets=("Chosen",))).convert(source)
    assert base64.b64encode(excluded.read_bytes()).decode() not in result.markdown
    assert "Excluded" not in result.markdown
    if selected_has_image:
        assert "Chosen — D5" in result.markdown
        assert result.markdown.index("## Chosen") < result.markdown.index("Image anchored at D5")
        assert base64.b64encode(allowed.read_bytes()).decode() in result.markdown
    else:
        assert "data:image/" not in result.markdown


@pytest.mark.parametrize("mode", ["pages", "images", "text"])
def test_pdf_media_is_attached_to_its_page(tmp_path, mode):
    source = tmp_path / "pages.pdf"
    Image.new("RGB", (24, 16), "navy").save(source, format="PDF", save_all=True,
        append_images=[Image.new("RGB", (24, 16), "red")])
    result = ConverterRouter(options=ConversionOptions(pdf_mode=mode)).convert(source)
    assert "HYBRIDPAGE" not in result.markdown
    if mode != "text":
        refs = list(re.finditer(r"!\[[^\]]*\]\[hybrid-media-[^\]]+\]", result.markdown))
        assert len(refs) == 2
        assert result.markdown.index("## Page 1") < refs[0].start() < result.markdown.index("## Page 2") < refs[1].start()
        _, assets = assert_package_resolves(result.markdown, tmp_path / "pages.zip")
        assert len(assets) == 2
    else:
        assert "data:image/" not in result.markdown


def test_appendix_policy_is_available(tmp_path):
    image = picture(tmp_path)
    source = tmp_path / "report.docx"
    doc = Document()
    doc.add_picture(str(image))
    doc.add_paragraph("End of source")
    doc.save(source)
    result = ConverterRouter(options=ConversionOptions(media_placement="appendix")).convert(source)
    assert result.markdown.index("End of source") < result.markdown.index("# Embedded document images") < result.markdown.index("![")


def test_package_preserves_code_examples_and_deduplicates_real_references(tmp_path):
    uri = "data:image/png;base64," + base64.b64encode(b"payload").decode()
    code = f"```md\n![example]({uri})\n```\n"
    inline_code = f"`![example]({uri})`\n"
    text = code + inline_code + f'![real]({uri})\n![reference][asset]\n[asset]: {uri}\n<img src="{uri}" alt="real">\n'
    output, assets = assert_package_resolves(text, tmp_path / "mixed.zip")
    assert code in output and inline_code in output
    assert len(assets) == 1
    assert output.count(next(iter(assets))) == 3


def test_package_failure_keeps_original_and_removes_temporary(tmp_path, monkeypatch):
    target = tmp_path / "result.zip"
    target.write_bytes(b"original")
    def fail(*args):
        raise OSError("simulated replace failure")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        AssetPackageExporter().export("content", target, overwrite=True)
    assert target.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [target]


def test_unsupported_inline_image_is_disclosed(tmp_path):
    class Base:
        def convert(self, source):
            return ConversionResult(source, "docx", "TOKEN", inline_images=(InlineImage("TOKEN", b"wmf", "image/x-wmf", "Original vector"),))
    class Empty:
        def extract(self, source, directory):
            return ()
    result = EmbeddedMediaDocumentConverter(Base(), Empty()).convert(tmp_path / "fake.docx")
    assert "Unsupported image" in result.markdown
    assert result.warnings and "TOKEN" not in result.markdown


def test_contextual_image_budget_is_enforced(tmp_path):
    image = picture(tmp_path)
    doc = Document()
    doc.add_picture(str(image))
    source = tmp_path / "large.docx"
    doc.save(source)
    with pytest.raises(ValueError, match="max_output_bytes"):
        ConverterRouter(options=ConversionOptions(max_output_bytes=32)).convert(source)


def test_pdf_native_jpeg_bytes_are_not_recompressed(tmp_path):
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    source = tmp_path / "native.pdf"
    Image.new("RGB", (24, 16), "navy").save(source, format="PDF")
    document = pdfium.PdfDocument(str(source))
    page = document[0]
    try:
        image = next(page.get_objects(filter=[raw.FPDF_PAGEOBJ_IMAGE]))
        assert "DCTDecode" in image.get_filters()
        original = bytes(image.get_data())
    finally:
        page.close()
        document.close()
    result = ConverterRouter(options=ConversionOptions(pdf_mode="images")).convert(source)
    payloads = list(definitions(result.markdown).values())
    assert len(payloads) == 1
    assert payloads[0].startswith("data:image/jpeg;base64,")
    assert base64.b64decode(payloads[0].split(",", 1)[1], validate=True) == original


def test_missing_position_falls_back_without_losing_image(tmp_path):
    class Base:
        def convert(self, source):
            return ConversionResult(source, "docx", "Retained text", inline_images=(InlineImage("ABSENT", b"payload", "image/png", "Figure"),))
    class Empty:
        def extract(self, source, directory):
            return ()
    result = EmbeddedMediaDocumentConverter(Base(), Empty()).convert(tmp_path / "fake.docx")
    assert result.markdown.startswith("Retained text")
    assert base64.b64encode(b"payload").decode() in result.markdown
    assert any("position" in warning for warning in result.warnings)


def test_package_rejects_malformed_base64_before_overwrite(tmp_path):
    target = tmp_path / "result.zip"
    target.write_bytes(b"original")
    with pytest.raises(ValueError):
        AssetPackageExporter().export("![bad](data:image/png;base64,a)", target, overwrite=True)
    assert target.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [target]
