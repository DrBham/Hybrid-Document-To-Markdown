"""Extract images from local document containers for Markdown embedding."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile


SUPPORTED_IMAGE_FORMATS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".svg"}
)


@dataclass(frozen=True, slots=True)
class ExtractedImage:
    path: Path
    context: str


class DocumentImageExtractor:
    """Extract OOXML media or render PDF pages into a temporary directory."""

    _MEDIA_PREFIXES = {
        ".docx": "word/media/",
        ".pptx": "ppt/media/",
        ".xlsx": "xl/media/",
    }

    def __init__(
        self,
        pdf_renderer: Callable[[Path, Path], tuple[ExtractedImage, ...]] | None = None,
    ):
        self._pdf_renderer = pdf_renderer or self._render_pdf_pages

    def extract(self, source: Path, output_directory: Path) -> tuple[ExtractedImage, ...]:
        suffix = source.suffix.lower()
        output_directory.mkdir(parents=True, exist_ok=True)
        if suffix == ".pdf":
            return self._pdf_renderer(source, output_directory)
        prefix = self._MEDIA_PREFIXES.get(suffix)
        if prefix is None:
            return ()
        return self._extract_ooxml(source, output_directory, prefix)

    @staticmethod
    def _extract_ooxml(
        source: Path,
        output_directory: Path,
        prefix: str,
    ) -> tuple[ExtractedImage, ...]:
        extracted: list[ExtractedImage] = []
        try:
            with ZipFile(source) as archive:
                members = sorted(
                    name
                    for name in archive.namelist()
                    if name.lower().startswith(prefix)
                    and Path(name).suffix.lower() in SUPPORTED_IMAGE_FORMATS
                )
                for index, member in enumerate(members, start=1):
                    original = Path(member).name
                    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", original)
                    target = output_directory / f"{index:04d}-{safe_name}"
                    target.write_bytes(archive.read(member))
                    extracted.append(
                        ExtractedImage(target, f"Embedded image: {original}")
                    )
        except BadZipFile as exc:
            raise ValueError(f"invalid {source.suffix.upper()} container") from exc
        return tuple(extracted)

    @staticmethod
    def _render_pdf_pages(
        source: Path,
        output_directory: Path,
    ) -> tuple[ExtractedImage, ...]:
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError(
                "PDF page embedding requires the installed PDF runtime"
            ) from exc

        document: Any = pdfium.PdfDocument(str(source))
        extracted: list[ExtractedImage] = []
        try:
            for page_index in range(len(document)):
                page = document[page_index]
                target = output_directory / f"page-{page_index + 1:04d}.png"
                bitmap = page.render(scale=2)
                bitmap.to_pil().save(target, format="PNG")
                extracted.append(
                    ExtractedImage(target, f"Rendered PDF page {page_index + 1}")
                )
                bitmap.close()
                page.close()
        finally:
            document.close()
        return tuple(extracted)
