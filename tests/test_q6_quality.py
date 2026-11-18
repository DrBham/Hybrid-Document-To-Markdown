"""Q6-B shared output contracts and ten-format quality gates."""

from pathlib import Path

import pytest

from document_converter.core.models import ConversionResult
from document_converter.core.options import ConversionOptions
from document_converter.core.router import ConverterRouter
from tools.q5_corpus import FORMATS, build, check, make_pdf


@pytest.mark.parametrize("extension", FORMATS)
def test_every_format_satisfies_shared_output_contract(tmp_path, extension):
    source, options, oracle = build(tmp_path, extension)

    result = ConverterRouter(options=options).convert(source)

    assert result.source_path.resolve() == source.resolve()
    assert result.source_format == extension
    assert result.markdown.encode("utf-8").decode("utf-8") == result.markdown
    assert "\x00" not in result.markdown
    assert all(warning and warning == " ".join(warning.split()) for warning in result.warnings)
    assert len(result.warnings) == len(set(result.warnings))
    assert all(check(result, oracle, tmp_path).values())


class BrokenConverter:
    def __init__(self, result):
        self.result = result

    def convert(self, _source):
        return self.result


def route_broken(tmp_path: Path, result):
    source = tmp_path / "source.txt"
    source.write_text("source", encoding="utf-8")
    return ConverterRouter({".txt": BrokenConverter(result)}).convert(source)


def test_output_contract_rejects_non_result(tmp_path):
    with pytest.raises(TypeError, match="ConversionResult"):
        route_broken(tmp_path, "not a result")


def test_output_contract_rejects_different_source(tmp_path):
    result = ConversionResult(tmp_path / "other.txt", "txt", "content")
    with pytest.raises(ValueError, match="source_path"):
        route_broken(tmp_path, result)


def test_output_contract_rejects_mismatched_format(tmp_path):
    result = ConversionResult(tmp_path / "source.txt", "pdf", "content")
    with pytest.raises(ValueError, match="source_format"):
        route_broken(tmp_path, result)


@pytest.mark.parametrize(
    "markdown, message",
    [
        ("bad\x00text", "NUL"),
        ("PRESERVEDTABLE" + "A" * 32, "placeholder"),
        ("\ud800", "UTF-8"),
    ],
)
def test_output_contract_rejects_unsafe_markdown(tmp_path, markdown, message):
    result = ConversionResult(tmp_path / "source.txt", "txt", markdown)
    with pytest.raises(ValueError, match=message):
        route_broken(tmp_path, result)


def test_output_contract_normalizes_and_deduplicates_warnings(tmp_path):
    result = ConversionResult(
        tmp_path / "source.txt",
        ".TXT",
        "content",
        ("  review   source  ", "review source", ""),
    )

    converted = route_broken(tmp_path, result)

    assert converted.source_format == "txt"
    assert converted.warnings == ("review source",)


def test_xlsx_metadata_can_be_embedded_or_omitted(tmp_path):
    from openpyxl import Workbook

    source = tmp_path / "metadata.xlsx"
    workbook = Workbook()
    workbook.active.append(["ID", "Value"])
    workbook.active.append(["00123", "1.2300"])
    workbook.save(source)
    workbook.close()

    embedded = ConverterRouter().convert(source).markdown
    omitted = ConverterRouter(
        options=ConversionOptions(metadata_mode="omit")
    ).convert(source).markdown

    assert "hybrid-metadata:spreadsheet-cells:start" in embedded
    assert "00123" in embedded and "00123" in omitted
    assert "hybrid-metadata:" not in omitted


def test_pptx_metadata_can_be_embedded_or_omitted(tmp_path):
    from pptx import Presentation

    source = tmp_path / "metadata.pptx"
    presentation = Presentation()
    presentation.slides.add_slide(presentation.slide_layouts[5]).shapes.title.text = "Title"
    presentation.save(source)

    embedded = ConverterRouter().convert(source).markdown
    omitted = ConverterRouter(
        options=ConversionOptions(metadata_mode="omit")
    ).convert(source).markdown

    assert "hybrid-metadata:presentation-structure:start" in embedded
    assert "Title" in embedded and "Title" in omitted
    assert "hybrid-metadata:" not in omitted


def test_metadata_mode_validation():
    with pytest.raises(ValueError, match="metadata_mode"):
        ConversionOptions(metadata_mode="hidden")


def _pdf_text(x, y, value):
    return f"BT /F1 12 Tf {x} {y} Td ({value}) Tj ET"


def _pdf_table_lines(horizontal):
    commands = [
        f"40 {y} m 560 {y} l S"
        for y in horizontal
    ]
    commands.extend([
        f"{x} {horizontal[-1]} m {x} {horizontal[0]} l S"
        for x in (40, 300, 560)
    ])
    return commands


def test_pdf_repairs_structured_wraps_and_stitches_continued_table(tmp_path):
    source = tmp_path / "continued-table.pdf"
    first_page = _pdf_table_lines((760, 700, 100, 40)) + [
        _pdf_text(50, 730, "Field"),
        _pdf_text(310, 730, "Value"),
        _pdf_text(50, 675, "JSON"),
        _pdf_text(310, 675, '{"request_id_unik":7'),
        _pdf_text(310, 655, "5}"),
        _pdf_text(310, 635, '{"request_id_unik":38'),
        _pdf_text(310, 615, ',"data_ganda":0}'),
        _pdf_text(50, 70, "Partisi total /"),
        _pdf_text(310, 70, "132 / 0 / 0"),
    ]
    second_page = _pdf_table_lines((760, 700, 640)) + [
        _pdf_text(50, 730, "pemilih ganda"),
        _pdf_text(50, 670, "Next field"),
        _pdf_text(310, 670, "Complete"),
    ]
    make_pdf(source, ["\n".join(first_page), "\n".join(second_page)])

    result = ConverterRouter(options=ConversionOptions(
        pdf_mode="text",
        metadata_mode="omit",
    )).convert(source)

    assert result.markdown.count("<table>") == 1
    assert "request_id_unik&quot;:75}" in result.markdown
    assert "request_id_unik&quot;:38,&quot;data_ganda&quot;:0}" in result.markdown
    assert "38<br>," not in result.markdown
    assert "Partisi total / pemilih ganda" in result.markdown
    assert "Next field" in result.markdown
    assert any("structured token" in warning for warning in result.warnings)
    assert any("table continuations" in warning for warning in result.warnings)


def test_pdf_repeated_header_starts_a_new_table(tmp_path):
    source = tmp_path / "separate-tables.pdf"
    page = _pdf_table_lines((760, 700, 40)) + [
        _pdf_text(50, 730, "Field"),
        _pdf_text(310, 730, "Value"),
        _pdf_text(50, 670, "Row"),
        _pdf_text(310, 670, "One"),
    ]
    make_pdf(source, ["\n".join(page), "\n".join(page)])

    result = ConverterRouter(options=ConversionOptions(
        pdf_mode="text",
        metadata_mode="omit",
    )).convert(source)

    assert result.markdown.count("<table>") == 2
    assert not any("table continuations" in warning for warning in result.warnings)
