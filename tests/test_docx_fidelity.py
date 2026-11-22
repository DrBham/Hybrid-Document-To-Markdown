"""Q6-C P0: Word equations, table headers, and numbering labels."""
import re

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from document_converter.core.router import ConverterRouter

MATH_NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'


def convert(document, path):
    document.save(path)
    return ConverterRouter().convert(path)


def add_math(paragraph, body, display=False):
    xml = f"<m:oMath {MATH_NS}>{body}</m:oMath>"
    if display:
        xml = f"<m:oMathPara {MATH_NS}>{xml}</m:oMathPara>"
    paragraph._p.append(parse_xml(xml))


def text(value):
    return f"<m:r><m:t>{value}</m:t></m:r>"


def test_inline_and_display_equations_become_latex(tmp_path):
    document = Document()
    paragraph = document.add_paragraph("Area ")
    # n-ary without m:chr is an integral by default.
    add_math(paragraph, "<m:nary><m:naryPr><m:limLoc m:val=\"subSup\"/></m:naryPr>"
                        f"<m:sub>{text('0')}</m:sub><m:sup>{text('t')}</m:sup><m:e>{text('x')}</m:e></m:nary>")
    paragraph.add_run(" (1)")
    add_math(document.add_paragraph(), f"<m:f><m:num>{text('a')}</m:num><m:den>{text('b')}</m:den></m:f>", display=True)
    result = convert(document, tmp_path / "math.docx")
    assert re.search(r"Area \$\\int_\{0\}\^\{t\}x\$ \(1\)", result.markdown)
    assert "$$\\frac{a}{b}$$" in result.markdown
    assert "HDMMATH" not in result.markdown


def test_unconvertible_equation_keeps_plain_text(tmp_path, monkeypatch):
    from document_converter.converters import docx_structure

    def fail(node):
        raise ValueError("unsupported")

    monkeypatch.setattr(docx_structure, "_latex", fail)
    document = Document()
    add_math(document.add_paragraph(), text("x+1"))
    result = convert(document, tmp_path / "fallback.docx")
    assert "`x+1`" in result.markdown
    assert any("LaTeX" in warning for warning in result.warnings)


def test_simple_table_uses_first_row_as_header(tmp_path):
    document = Document()
    table = document.add_table(rows=3, cols=2)
    for row, values in zip(table.rows, [("Name", "Score"), ("Ada", "00123"), ("Lin", "")]):
        for cell, value in zip(row.cells, values):
            cell.text = value
    table.cell(0, 0).paragraphs[0].runs[0].bold = True
    result = convert(document, tmp_path / "table.docx")
    lines = [line for line in result.markdown.splitlines() if line.startswith("|")]
    assert lines[0].replace(" ", "") == "|Name|Score|"
    assert set(lines[1].replace("|", "").replace(" ", "")) == {"-"}
    assert lines[2].replace(" ", "") == "|Ada|00123|"
    assert len(lines) == 4


def add_numbering(document, abstract_id, levels, num_id, start_override=None):
    numbering = document.part.numbering_part.element
    lvls = "".join(
        f'<w:lvl w:ilvl="{index}"><w:start w:val="{start}"/><w:numFmt w:val="{fmt}"/>'
        f'<w:lvlText w:val="{label}"/></w:lvl>'
        for index, (fmt, label, start) in enumerate(levels)
    )
    numbering.insert(0, parse_xml(f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{abstract_id}">{lvls}</w:abstractNum>'))
    override = ""
    if start_override is not None:
        override = f'<w:lvlOverride w:ilvl="0"><w:startOverride w:val="{start_override}"/></w:lvlOverride>'
    numbering.append(parse_xml(f'<w:num {nsdecls("w")} w:numId="{num_id}"><w:abstractNumId w:val="{abstract_id}"/>{override}</w:num>'))


def numbered(document, value, num_id, level=0):
    paragraph = document.add_paragraph(value)
    paragraph._p.get_or_add_pPr().append(parse_xml(
        f'<w:numPr {nsdecls("w")}><w:ilvl w:val="{level}"/><w:numId w:val="{num_id}"/></w:numPr>'))
    return paragraph


def test_numbering_keeps_source_labels(tmp_path):
    document = Document()
    add_numbering(document, 90, [("decimal", "%1.", 1), ("decimal", "%1.%2.", 1), ("decimal", "%1.%2.%3.", 1)], 901)
    add_numbering(document, 91, [("lowerLetter", "%1.", 1)], 911)
    add_numbering(document, 91, [("lowerLetter", "%1.", 1)], 912, start_override=1)
    add_numbering(document, 92, [("decimal", "[%1]", 1)], 921)
    numbered(document, "Intro", 901)
    numbered(document, "Method", 901)
    numbered(document, "Design", 901, 1)
    numbered(document, "Detail", 901, 2)
    numbered(document, "Sample", 901, 1)
    numbered(document, "First point", 911)
    numbered(document, "Second point", 911)
    document.add_paragraph("Body text")
    numbered(document, "Restarted", 912)
    numbered(document, "Ref one", 921)
    numbered(document, "Ref two", 921)
    result = convert(document, tmp_path / "numbering.docx")
    markdown = result.markdown
    for expected in ["1. Intro", "2. Method", "2.1. Design", "2.1.1. Detail", "2.2. Sample",
                     "a. First point", "b. Second point", "a. Restarted", "[1] Ref one", "[2] Ref two"]:
        assert re.search(rf"^\s*(- )?{re.escape(expected)}$", markdown, re.M), expected
    assert "HDMLIST" not in markdown
    assert markdown.index("Intro") < markdown.index("Detail") < markdown.index("Body text") < markdown.index("Ref two")


def test_bullets_nest_under_numbered_items(tmp_path):
    document = Document()
    add_numbering(document, 93, [("decimal", "%1.", 1), ("bullet", "•", 1)], 931)
    numbered(document, "Parent", 931)
    numbered(document, "Child one", 931, 1)
    numbered(document, "Child two", 931, 1)
    numbered(document, "Next parent", 931)
    markdown = convert(document, tmp_path / "bullets.docx").markdown
    assert "1. Parent\n   - Child one\n   - Child two\n2. Next parent" in markdown


def test_style_linked_numbering_is_labelled(tmp_path):
    document = Document()
    add_numbering(document, 94, [("upperRoman", "%1.", 1)], 941)
    style = document.styles.add_style("Numbered Heading", 1)
    style.element.get_or_add_pPr().append(parse_xml(
        f'<w:numPr {nsdecls("w")}><w:numId w:val="941"/></w:numPr>'))
    for value in ("Scope", "Results"):
        document.add_paragraph(value, style="Numbered Heading")
    markdown = convert(document, tmp_path / "styled.docx").markdown
    assert "I. Scope" in markdown and "II. Results" in markdown


# --- Q6-C P1: headings, run spacing, formatting overrides, alt text, columns ---


def bold_paragraph(document, value, style=None):
    paragraph = document.add_paragraph(style=style)
    paragraph.add_run(value).bold = True
    return paragraph


def test_headings_without_word_heading_styles(tmp_path):
    document = Document()
    document.add_paragraph("Study Title", style="Title")
    add_numbering(document, 95, [("decimal", "%1.", 1), ("decimal", "%1.%2.", 1)], 951)
    numbered(document, "", 951).add_run("INTRODUCTION").bold = True
    document.add_paragraph("Body.")
    numbered(document, "", 951, 1).add_run("Data Sources").bold = True
    bold_paragraph(document, "REFERENCES")
    numbered(document, "", 951).add_run("Ordinary bold item").bold = True
    bold_paragraph(document, "THIS LONG BOLD UPPERCASE NOTICE KEEPS GOING FOR MORE THAN EIGHT WORDS")
    outline = document.add_paragraph("Appendix overview")
    outline._p.get_or_add_pPr().append(parse_xml(f'<w:outlineLvl {nsdecls("w")} w:val="1"/>'))
    result = convert(document, tmp_path / "headings.docx")
    markdown = result.markdown
    for line in ["# Study Title", "## 1. INTRODUCTION", "### 1.1. Data Sources", "## REFERENCES", "## Appendix overview"]:
        assert re.search(rf"^{re.escape(line)}$", markdown, re.M), line
    assert re.search(r"^2\. \*\*Ordinary bold item\*\*$", markdown, re.M)
    assert not re.search(r"^#+ THIS LONG", markdown, re.M)
    assert not any("HDMHeading" in warning for warning in result.warnings)


def test_whitespace_runs_keep_words_apart(tmp_path):
    document = Document()
    paragraph = document.add_paragraph("Before ")
    for value in ("Sample", " ", "Figure"):
        paragraph.add_run(value).bold = True
    markdown = convert(document, tmp_path / "spacing.docx").markdown
    assert "SampleFigure" not in markdown
    assert re.search(r"\*\*Sample\*\* ?\*\*Figure\*\*|\*\*Sample Figure\*\*", markdown)


def test_direct_bold_off_overrides_strong_style(tmp_path):
    document = Document()
    paragraph = document.add_paragraph()
    plain = paragraph.add_run("Author, A. ")
    plain.style = "Strong"
    plain.bold = False
    paragraph.add_run("Title").bold = True
    markdown = convert(document, tmp_path / "strong.docx").markdown
    assert "Author, A. **Title**" in markdown


def png_bytes(width, height):
    from io import BytesIO
    from PIL import Image
    buffer = BytesIO()
    Image.new("RGB", (width, height), (40, 120, 200)).save(buffer, "PNG")
    return buffer.getvalue()


def picture(document, path, descr=None):
    document.add_picture(str(path))
    properties = document.paragraphs[-1]._p.xpath(".//wp:docPr")[0]
    if descr is None:
        properties.attrib.pop("descr", None)
    else:
        properties.set("descr", descr)


def alt_texts(markdown):
    return re.findall(r"!\[([^\]]*)\]", markdown)


def test_image_alt_text_uses_nearest_caption(tmp_path):
    image = tmp_path / "pixel.png"
    image.write_bytes(png_bytes(8, 8))
    document = Document()
    picture(document, image, "㿷᛿॰")
    document.add_paragraph("Figure 2: Network map")
    document.add_paragraph("Unrelated body text.")
    picture(document, image, "Sales chart")
    document.add_paragraph("Body text only.")
    picture(document, image, "")
    document.add_paragraph("No caption here.")
    alts = alt_texts(convert(document, tmp_path / "alt.docx").markdown)
    assert alts[:3] == ["Figure 2: Network map", "Sales chart", "Word document image"]


def test_two_column_docx_keeps_order_and_full_resolution_image(tmp_path):
    import base64
    original = png_bytes(2400, 1600)
    image = tmp_path / "large.png"
    image.write_bytes(original)
    document = Document()
    document.add_paragraph("Column one start")
    picture(document, image)
    document.add_paragraph("Figure 1. Large chart")
    document.add_paragraph("Column one end")
    document.add_paragraph("Column two start")
    document.add_paragraph("Column two end")
    columns = document.sections[0]._sectPr
    columns.append(parse_xml(f'<w:cols {nsdecls("w")} w:num="2" w:space="720"/>'))
    markdown = convert(document, tmp_path / "columns.docx").markdown
    order = ["Column one start", "Figure 1. Large chart", "Column one end", "Column two start", "Column two end"]
    positions = [markdown.index(value) for value in order]
    assert positions == sorted(positions)
    payloads = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", markdown)
    assert [base64.b64decode(payload) for payload in payloads] == [original]
