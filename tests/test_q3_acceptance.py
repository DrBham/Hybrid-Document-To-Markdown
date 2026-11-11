"""Source-backed complex-format acceptance fixtures for Q3."""
import json
from copy import deepcopy
import re
from zipfile import ZipFile, ZIP_DEFLATED

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from openpyxl import Workbook
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.util import Inches
import pytest

from document_converter.core.options import ConversionOptions
from document_converter.core.router import ConverterRouter


def rewrite_archive(source, transform):
    with ZipFile(source) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    transform(parts)
    with ZipFile(source, "w", ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)


def make_pdf(source, commands, media_box="0 0 600 800"):
    """Small valid vector PDF with exact known text and line coordinates."""
    stream = commands.encode("ascii")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               f"<< /Type /Page /Parent 2 0 R /MediaBox [{media_box}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode(),
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    content = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(content)
    content.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets:
        content.extend(f"{offset:010d} 00000 n \n".encode())
    content.extend(f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    source.write_bytes(content)


def text(x, y, value):
    return f"BT /F1 12 Tf {x} {y} Td ({value}) Tj ET\n"


def test_pdf_two_columns_read_down_each_column(tmp_path):
    source = tmp_path / "columns.pdf"
    make_pdf(source, text(30, 750, "LEFT FIRST") + text(330, 750, "RIGHT FIRST") + text(30, 720, "LEFT SECOND") + text(330, 720, "RIGHT SECOND"))
    result = ConverterRouter(options=ConversionOptions(pdf_columns=2, pdf_mode="text")).convert(source)
    assert result.markdown.index("LEFT FIRST") < result.markdown.index("LEFT SECOND") < result.markdown.index("RIGHT FIRST") < result.markdown.index("RIGHT SECOND")
    assert "## Page 1" in result.markdown


def test_pdf_merged_table_retains_span_and_multiline_cell(tmp_path):
    source = tmp_path / "merged.pdf"
    lines = "\n".join(f"{x0} {y0} m {x1} {y1} l S" for x0, y0, x1, y1 in [
        (40, 700, 440, 700), (40, 650, 440, 650), (40, 580, 440, 580),
        (40, 580, 40, 700), (440, 580, 440, 700), (240, 580, 240, 650)])
    make_pdf(source, lines + "\n" + text(60, 675, "MERGED HEADER") + text(60, 625, "00123") + text(260, 625, "line one") + text(260, 605, "line two"))
    result = ConverterRouter(options=ConversionOptions(pdf_mode="text")).convert(source)
    assert '<td colspan="2" rowspan="1">MERGED HEADER</td>' in result.markdown
    assert "line one<br>line two" in result.markdown
    data = json.loads(re.search(r"```json\n(.*?)\n```", result.markdown, re.S).group(1))
    assert len(data["cells"]) == 3
    assert data["rows"][1] == ["00123", "line one\nline two"]


def test_word_merged_and_nested_tables_stay_semantic(tmp_path):
    source = tmp_path / "tables.docx"
    document = Document()
    document.add_heading("Start", 1)
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "Merged heading"
    table.cell(1, 0).text = "00123"
    nested = table.cell(1, 1).add_table(rows=1, cols=1)
    nested.cell(0, 0).text = "Nested value"
    document.add_paragraph("End")
    document.save(source)
    result = ConverterRouter().convert(source)
    assert 'colspan="2"' in result.markdown
    assert result.markdown.count("<table>") == 2
    assert result.markdown.index("# Start") < result.markdown.index("00123") < result.markdown.index("Nested value") < result.markdown.index("End")
    assert result.warnings


def test_word_footnote_reference_and_body_are_preserved(tmp_path):
    source = tmp_path / "notes.docx"
    document = Document()
    paragraph = document.add_paragraph("Claim")
    reference = OxmlElement("w:footnoteReference")
    reference.set(qn("w:id"), "1")
    paragraph.add_run()._r.append(reference)
    document.save(source)
    def add_notes(parts):
        parts["word/footnotes.xml"] = b'<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:footnote w:id="1"><w:p><w:r><w:t>Source note 00123</w:t></w:r></w:p></w:footnote></w:footnotes>'
        parts["word/_rels/document.xml.rels"] = parts["word/_rels/document.xml.rels"].replace(b"</Relationships>", b'<Relationship Id="rIdFootnotes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/></Relationships>')
        parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(b"</Types>", b'<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/></Types>')
    rewrite_archive(source, add_notes)
    result = ConverterRouter().convert(source)
    assert "Source note 00123" in result.markdown
    assert "#footnote-1" in result.markdown and 'id="footnote-1"' in result.markdown
    assert 'id="footnote-ref-1"' in result.markdown


def test_word_nested_numbering(tmp_path):
    source = tmp_path / "lists.docx"
    document = Document()
    numbering = document.part.numbering_part.element
    num_definition = next(node for node in numbering.findall(qn("w:num")) if node.get(qn("w:numId")) == "5")
    abstract_id = num_definition.find(qn("w:abstractNumId")).get(qn("w:val"))
    abstract = next(node for node in numbering.findall(qn("w:abstractNum")) if node.get(qn("w:abstractNumId")) == abstract_id)
    nested_level = deepcopy(abstract.find(qn("w:lvl")))
    nested_level.set(qn("w:ilvl"), "1")
    abstract.append(nested_level)
    for value, level in [("Parent", 0), ("Child", 1), ("Next parent", 0)]:
        p = document.add_paragraph(value)
        num = OxmlElement("w:numPr")
        for tag, val in [("w:ilvl", str(level)), ("w:numId", "5")]:
            node = OxmlElement(tag)
            node.set(qn("w:val"), val)
            num.append(node)
        p._p.get_or_add_pPr().append(num)
    document.save(source)
    result = ConverterRouter().convert(source)
    assert "1. Parent" in result.markdown
    assert re.search(r"\n +1\. Child", result.markdown)
    assert "2. Next parent" in result.markdown


def test_presentation_chart_and_connector_source(tmp_path):
    source = tmp_path / "diagram.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    slide.shapes.title.text = "Network"
    first = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1), Inches(1), Inches(1), Inches(1))
    first.text = "Router"
    second = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(3), Inches(1), Inches(1), Inches(1))
    second.text = "Switch"
    connection = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, 0, 0, Inches(1), Inches(1))
    connection.begin_connect(first, 0)
    connection.end_connect(second, 0)
    data = CategoryChartData()
    data.categories = ["Jan", "Feb"]
    data.add_series("Traffic", [1.25, 2.5])
    slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(3), Inches(5), Inches(2), data)
    presentation.save(source)
    result = ConverterRouter().convert(source)
    records = json.loads(re.search(r"```json\n(.*?)\n```", result.markdown, re.S).group(1))
    connector = next(s for s in records[0]["shapes"] if s["kind"] == "cxnSp")
    assert [c["id"] for c in connector["connections"]] == [str(first.shape_id), str(second.shape_id)]
    assert "Traffic" in result.markdown and "1.25" in result.markdown and "2.5" in result.markdown
    assert "ppt/charts/chart1.xml" in result.markdown


@pytest.mark.parametrize("literal", ["1.2300", "9007199254740993", "0.123456789012345678901"])
def test_xlsx_numeric_lexeme_not_rounded(tmp_path, literal):
    source = tmp_path / "numeric.xlsx"
    workbook = Workbook()
    workbook.active.append(["Value"])
    workbook.active.append([1])
    workbook.save(source)
    def replace_value(parts):
        parts["xl/worksheets/sheet1.xml"] = parts["xl/worksheets/sheet1.xml"].replace(b"<v>1</v>", f"<v>{literal}</v>".encode())
    rewrite_archive(source, replace_value)
    result = ConverterRouter().convert(source)
    assert f"| {literal} |" in result.markdown
    records = json.loads(re.search(r"```json\n(.*?)\n```", result.markdown, re.S).group(1))
    assert next(cell for cell in records["cells"] if cell["cell"] == "A2")["xml_value"] == literal


def test_html_merged_table_preserves_spans(tmp_path):
    source = tmp_path / "merged.html"
    source.write_text('<table><tr><th colspan="2">Heading</th></tr><tr><td>00123</td><td>Value</td></tr></table>')
    result = ConverterRouter().convert(source)
    assert 'colspan="2"' in result.markdown and "00123" in result.markdown
    assert result.warnings


def test_prose_is_explicit_and_warns(tmp_path):
    source = tmp_path / "prose.txt"
    source.write_bytes(b"First line\nsecond line\n\nAnother paragraph")
    result = ConverterRouter(options=ConversionOptions(text_mode="prose")).convert(source)
    assert result.markdown == "First line second line\n\nAnother paragraph"
    assert result.warnings


@pytest.mark.parametrize("keyword", [{"pdf_columns": 3}, {"text_mode": "guess"}])
def test_rejects_unsupported_layout_policies(keyword):
    with pytest.raises(ValueError):
        ConversionOptions(**keyword)


def test_html_code_inside_merged_table_stays_html(tmp_path):
    source = tmp_path / "code-table.html"
    source.write_bytes(b'<table><tr><td colspan="2"><pre>  code  \n\nend</pre></td></tr></table>')
    result = ConverterRouter().convert(source)
    assert '<pre>  code  \n\nend</pre>' in result.markdown
    assert "PRESERVED" not in result.markdown


def test_pdf_nonzero_page_origin(tmp_path):
    source = tmp_path / "offset.pdf"
    make_pdf(source, text(50, 750, "OFFSET CONTENT"), media_box="20 30 620 830")
    result = ConverterRouter(options=ConversionOptions(pdf_mode="text")).convert(source)
    assert "OFFSET CONTENT" in result.markdown
