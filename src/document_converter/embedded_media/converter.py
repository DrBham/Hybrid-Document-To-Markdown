"""Append document images to Markdown as Base64 data URIs."""

from __future__ import annotations

import base64
from pathlib import Path
from tempfile import TemporaryDirectory

from ..core.base_converter import BaseConverter
from ..core.models import ConversionResult
from ..core.options import ConversionOptions
from .extractor import DocumentImageExtractor, ExtractedImage


MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".svg": "image/svg+xml",
}


def encode_image_data_uri(image_path: Path) -> str:
    """Encode one supported image as a self-contained data URI."""

    mime_type = MIME_TYPES.get(image_path.suffix.lower())
    if mime_type is None:
        raise ValueError(f"unsupported embedded image format: {image_path.suffix}")
    payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"


def _safe_alt_text(value: str) -> str:
    return value.replace("[", "(").replace("]", ")").replace("\n", " ")


def _render_image(image: ExtractedImage) -> str:
    alt_text = _safe_alt_text(image.context)
    return f"## {image.context}\n\n![{alt_text}]({encode_image_data_uri(image.path)})"


class EmbeddedMediaDocumentConverter(BaseConverter):
    """Decorate document conversion with automatic single-file image embedding."""

    def __init__(
        self,
        base_converter: BaseConverter,
        extractor: DocumentImageExtractor | None = None,
        *, options: ConversionOptions | None = None,
    ):
        self.options = options or ConversionOptions()
        self._base_converter = base_converter
        self._extractor = extractor or DocumentImageExtractor(options=self.options)

    def convert(self, file_path: Path) -> ConversionResult:
        base_result = self._base_converter.convert(file_path)
        warnings = list(base_result.warnings)
        if file_path.suffix.lower() == ".pdf":
            if not base_result.markdown.strip():
                warnings.append("No PDF text layer was extracted. Images are not OCR text.")
            if self.options.pdf_mode == "images":
                warnings.append("PDF image extraction may re-encode images and omit masks/vector artwork; use pages mode for page appearance.")
            warnings.append("PDF reading order and complex tables require source review.")
        with TemporaryDirectory(prefix="hybrid-document-media-") as temporary:
            images = self._extractor.extract(file_path, Path(temporary))
            sections = []
            used = len(base_result.markdown.encode("utf-8"))
            for image in images:
                expected = 4 * ((image.path.stat().st_size + 2) // 3)
                if used + expected > self.options.max_output_bytes:
                    raise ValueError("Embedded images exceed max_output_bytes")
                section = _render_image(image)
                used += len(section.encode("utf-8"))
                sections.append(section)

        # Media embedding must not normalize text produced by the converter.
        # Trailing spaces can encode Markdown hard breaks or preformatted data.
        markdown = base_result.markdown
        if sections:
            separator = "" if markdown.endswith("\n\n") else (
                "\n" if markdown.endswith("\n") else "\n\n"
            )
            markdown += (
                separator + "---\n\n# Embedded document images\n\n"
                "> Images are stored inside this Markdown file as Base64 data URIs. "
                "A compatible Markdown or multimodal AI client can decode them.\n\n"
                + "\n\n".join(sections)
                + "\n"
            )

        return ConversionResult(
            source_path=base_result.source_path,
            source_format=base_result.source_format,
            markdown=markdown,
            warnings=tuple(warnings),
        )
