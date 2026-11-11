"""Append document images to Markdown as Base64 data URIs."""

from __future__ import annotations

import base64
import hashlib
import html
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
    return html.escape(value, quote=False).replace("\\", "\\\\").replace("[", "(").replace("]", ")").replace("\n", " ").replace("\r", " ")


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
        if base_result.inline_images or base_result.page_media_slots or (file_path.suffix.lower() == ".xlsx" and self.options.sheets):
            return self._place_media(file_path, base_result)
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
            if self.options.media_placement == "context":
                warnings.append("Source media has no verified inline position; preserved in appendix.")
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

    def _place_media(self, file_path, result):
        markdown = result.markdown
        warnings = list(result.warnings)
        definitions, uri_cache, appendix = {}, {}, []
        provenance = []
        seen = set()
        used = len(markdown.encode("utf-8"))

        def render(data, mime, label, as_html=False):
            nonlocal used
            if mime not in MIME_TYPES.values():
                warnings.append(f"Unsupported embedded image type: {mime}. Image could not be rendered.")
                return "[Unsupported image: " + _safe_alt_text(label) + "]"
            digest = hashlib.sha256(data).hexdigest()
            seen.add(digest)
            key = (digest, mime)
            if key not in uri_cache:
                expected = 4 * ((len(data) + 2) // 3)
                if used + expected > self.options.max_output_bytes:
                    raise ValueError("Embedded images exceed max_output_bytes")
                uri_cache[key] = f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
                used += expected
            if as_html:
                return f'<img alt="{html.escape(label, quote=True)}" src="{uri_cache[key]}">'
            if key not in definitions:
                name = "hybrid-media-" + digest
                while f"[{name}]" in result.markdown or any(v[0] == name for v in definitions.values()):
                    name += "-image"
                definitions[key] = (name, uri_cache[key])
            return f"![{_safe_alt_text(label)}][{definitions[key][0]}]"

        for item in result.inline_images:
            rendered = render(item.data, item.mime_type, item.label, item.html and self.options.media_placement == "context")
            if item.token not in markdown:
                warnings.append("An image source position was unavailable; image preserved in appendix.")
                appendix.append(rendered)
            elif self.options.media_placement == "appendix":
                markdown = markdown.replace(item.token, "")
                appendix.append(rendered)
            else:
                markdown = markdown.replace(item.token, rendered)

        with TemporaryDirectory(prefix="hybrid-document-media-") as temporary:
            images = self._extractor.extract(file_path, Path(temporary))
            page_images = {}
            for image in images:
                data = image.path.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                if image.page is None and digest in seen:
                    provenance.append("<!-- Source media: " + html.escape(image.context).replace("--", "—") + " -->")
                    continue
                # Selected-sheet conversion must never append other sheets' assets.
                if file_path.suffix.lower() == ".xlsx" and self.options.sheets and image.page is None:
                    continue
                mime = MIME_TYPES.get(image.path.suffix.lower(), "application/octet-stream")
                rendered = render(data, mime, image.context)
                if image.page is not None and self.options.media_placement == "context":
                    page_images.setdefault(image.page, []).append(rendered)
                else:
                    appendix.append(rendered)
                    if self.options.media_placement == "context":
                        warnings.append("Additional source media has no verified inline position; preserved in appendix.")
            for slot in result.page_media_slots:
                markdown = markdown.replace(slot.token, "\n\n".join(page_images.pop(slot.page, [])))
            for remaining in page_images.values():
                appendix.extend(remaining)
                warnings.append("PDF image page marker unavailable; preserved in appendix.")

        if appendix or definitions:
            separator = "" if markdown.endswith("\n\n") else ("\n" if markdown.endswith("\n") else "\n\n")
            markdown += separator + "---\n\n# Embedded document images\n\n"
            if provenance:
                markdown += "\n".join(dict.fromkeys(provenance)) + "\n\n"
            if appendix:
                markdown += "\n\n".join(appendix) + "\n\n"
            markdown += "\n".join(f"[{name}]: {uri}" for name, uri in definitions.values()) + "\n"
        if len(markdown.encode("utf-8")) > self.options.max_output_bytes:
            raise ValueError("Markdown exceeds max_output_bytes")
        if file_path.suffix.lower() == ".pdf" and self.options.pdf_mode == "images":
            warnings.append("PDF images may be re-encoded and omit masks/vector artwork; use pages mode for page appearance.")
        return ConversionResult(result.source_path, result.source_format, markdown, tuple(dict.fromkeys(warnings)))
