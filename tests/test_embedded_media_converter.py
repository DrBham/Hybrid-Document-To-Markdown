import base64
import re
from pathlib import Path

from docx import Document
from PIL import Image

from document_converter.core.router import ConverterRouter
from document_converter.core.models import ConversionResult
from document_converter.embedded_media.converter import (
    EmbeddedMediaDocumentConverter,
    encode_image_data_uri,
)
from document_converter.embedded_media.extractor import ExtractedImage


class FakeConverter:
    def convert(self, file_path):
        return ConversionResult(file_path, "docx", "# Existing document\n")


class FakeExtractor:
    def extract(self, source, output_directory):
        image = output_directory / "embedded.png"
        image.write_bytes(b"fixture")
        return (ExtractedImage(image, "Embedded image: diagram.png"),)


def test_encodes_image_as_base64_data_uri(tmp_path):
    image = tmp_path / "diagram.png"
    image.write_bytes(b"image bytes")

    uri = encode_image_data_uri(image)

    expected = base64.b64encode(b"image bytes").decode("ascii")
    assert uri == f"data:image/png;base64,{expected}"


def test_converter_embeds_image_inside_single_markdown_result(tmp_path):
    source = tmp_path / "network.docx"
    source.write_bytes(b"fixture")
    converter = EmbeddedMediaDocumentConverter(FakeConverter(), FakeExtractor())

    result = converter.convert(source)

    assert result.markdown.startswith("# Existing document")
    assert "# Embedded document images" in result.markdown
    assert "Embedded image: diagram.png" in result.markdown
    assert "data:image/png;base64," in result.markdown
    assert base64.b64encode(b"fixture").decode("ascii") in result.markdown


def test_converter_leaves_text_only_markdown_without_media_section(tmp_path):
    class EmptyExtractor:
        def extract(self, source, output_directory):
            return ()

    source = tmp_path / "notes.txt"
    source.write_text("content", encoding="utf-8")
    result = EmbeddedMediaDocumentConverter(
        FakeConverter(), EmptyExtractor()
    ).convert(source)

    assert result.markdown == "# Existing document\n"


def test_default_router_embeds_real_docx_image_in_markdown(tmp_path):
    image = tmp_path / "topology.png"
    Image.new("RGB", (48, 32), "navy").save(image)
    document = tmp_path / "network.docx"
    source = Document()
    source.add_heading("Network document", level=1)
    source.add_picture(str(image))
    source.save(document)

    result = ConverterRouter().convert(document)

    assert "Network document" in result.markdown
    assert "# Embedded document images" in result.markdown
    match = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", result.markdown)
    assert match is not None
    decoded = base64.b64decode(match.group(1))
    assert decoded.startswith(b"\x89PNG\r\n\x1a\n")
