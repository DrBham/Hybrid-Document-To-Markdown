from zipfile import ZipFile

import pytest

from document_converter.embedded_media.extractor import DocumentImageExtractor


@pytest.mark.parametrize(
    "extension, media_prefix",
    [
        (".docx", "word/media/"),
        (".pptx", "ppt/media/"),
        (".xlsx", "xl/media/"),
    ],
)
def test_extracts_only_supported_ooxml_media(
    tmp_path, extension, media_prefix
):
    document = tmp_path / f"diagram{extension}"
    with ZipFile(document, "w") as archive:
        archive.writestr(f"{media_prefix}network.png", b"png")
        archive.writestr(f"{media_prefix}vector.svg", b"svg")

    images = DocumentImageExtractor().extract(document, tmp_path / "output")

    assert len(images) == 2
    assert images[0].path.read_bytes() == b"png"
    assert images[0].context == "Embedded image: network.png"
    assert images[1].path.read_bytes() == b"svg"
    assert images[1].context == "Embedded image: vector.svg"


def test_delegates_pdf_rendering(tmp_path):
    document = tmp_path / "scan.pdf"
    document.write_bytes(b"pdf")
    calls = []

    def renderer(source, output):
        calls.append((source, output))
        return ()

    images = DocumentImageExtractor(pdf_renderer=renderer).extract(
        document, tmp_path / "pages"
    )

    assert images == ()
    assert calls[0][0] == document


def test_renders_real_pdf_page_locally(tmp_path):
    pillow = pytest.importorskip("PIL.Image")
    document = tmp_path / "scan.pdf"
    pillow.new("RGB", (32, 24), "white").save(document, format="PDF")

    images = DocumentImageExtractor().extract(document, tmp_path / "pages")

    assert len(images) == 1
    assert images[0].path.suffix == ".png"
    assert images[0].path.stat().st_size > 0
    assert images[0].context == "Rendered PDF page 1"
