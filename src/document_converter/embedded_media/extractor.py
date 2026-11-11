"""Extract images from local document containers for Markdown embedding."""

from __future__ import annotations

import re
import posixpath
from xml.etree import ElementTree
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile
from ..core.options import ConversionOptions


SUPPORTED_IMAGE_FORMATS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".svg"}
)


@dataclass(frozen=True, slots=True)
class ExtractedImage:
    path: Path
    context: str
    page: int | None = None


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
        *, options: ConversionOptions | None = None,
    ):
        self.options = options or ConversionOptions()
        self._pdf_renderer = pdf_renderer or self._render_pdf_pages

    def extract(self, source: Path, output_directory: Path) -> tuple[ExtractedImage, ...]:
        suffix = source.suffix.lower()
        output_directory.mkdir(parents=True, exist_ok=True)
        if suffix == ".pdf":
            if self.options.pdf_mode == "text":
                return ()
            return self._pdf_renderer(source, output_directory)
        prefix = self._MEDIA_PREFIXES.get(suffix)
        if prefix is None:
            return ()
        return self._extract_ooxml(source, output_directory, prefix)

    def _extract_ooxml(
        self,
        source: Path,
        output_directory: Path,
        prefix: str,
    ) -> tuple[ExtractedImage, ...]:
        extracted: list[ExtractedImage] = []
        try:
            with ZipFile(source) as archive:
                if len(archive.infolist()) > self.options.max_archive_entries or sum(
                    item.file_size for item in archive.infolist()
                ) > self.options.max_uncompressed_bytes:
                    raise ValueError("Archive exceeds extraction budget")
                members = sorted(
                    name
                    for name in archive.namelist()
                    if name.lower().startswith(prefix)
                    and Path(name).suffix.lower() in SUPPORTED_IMAGE_FORMATS
                )
                contexts = {}
                ordered = []
                for rel_name in sorted(archive.namelist(), key=lambda name: [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", name)]):
                    if not rel_name.endswith(".rels") or "/_rels/" not in rel_name:
                        continue
                    base, filename = rel_name.rsplit("/_rels/", 1)
                    owner = base + "/" + filename[:-5]
                    if owner not in archive.namelist():
                        continue
                    relationships = self._safe_xml(archive.read(rel_name))
                    lookup = {}
                    for relation in relationships:
                        if relation.get("TargetMode") == "External":
                            continue
                        target = posixpath.normpath(posixpath.join(base, relation.get("Target", ""))).lstrip("/")
                        if target in members:
                            lookup[relation.get("Id")] = target
                    if not lookup:
                        continue
                    owner_xml = self._safe_xml(archive.read(owner))
                    for element in owner_xml.iter():
                        for key, value in element.attrib.items():
                            if key.startswith("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}") and value in lookup:
                                target = lookup[value]
                                contexts.setdefault(target, []).append(owner)
                                if target not in ordered:
                                    ordered.append(target)
                members = ordered + [member for member in members if member not in ordered]
                for index, member in enumerate(members, start=1):
                    original = Path(member).name
                    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", original)
                    target = output_directory / f"{index:04d}-{safe_name}"
                    target.write_bytes(archive.read(member))
                    extracted.append(
                        ExtractedImage(target, f"Embedded image: {original}" + (
                            " — " + ", ".join(dict.fromkeys(contexts[member])) if member in contexts else ""
                        ))
                    )
        except BadZipFile as exc:
            raise ValueError(f"invalid {source.suffix.upper()} container") from exc
        return tuple(extracted)

    @staticmethod
    def _safe_xml(data):
        if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
            raise ValueError("DTD/entity declarations are unsupported in OOXML relationships")
        return ElementTree.fromstring(data)

    def _render_pdf_pages(
        self,
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
            if len(document) > self.options.max_pdf_pages:
                raise ValueError("PDF exceeds max_pdf_pages")
            total_bytes = 0
            for page_index in range(len(document)):
                page = document[page_index]
                target = output_directory / f"page-{page_index + 1:04d}.png"
                bitmap = None
                try:
                    if self.options.pdf_mode == "images":
                        import pypdfium2.raw as raw
                        for index, obj in enumerate(page.get_objects(filter=[raw.FPDF_PAGEOBJ_IMAGE]), 1):
                            info = obj.get_metadata()
                            if info.width * info.height > self.options.max_page_pixels:
                                raise ValueError("PDF image exceeds max_page_pixels")
                            prefix = output_directory / f"page-{page_index + 1:04d}-image-{index:04d}"
                            obj.extract(prefix, fb_format="png")
                            candidates = list(output_directory.glob(prefix.name + ".*"))
                            for image_path in candidates:
                                if image_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
                                    raise ValueError("PDF image encoding unsupported; use pages mode")
                                total_bytes += image_path.stat().st_size
                                if total_bytes > self.options.max_uncompressed_bytes:
                                    raise ValueError("PDF images exceed media budget")
                                extracted.append(ExtractedImage(image_path, f"PDF page {page_index + 1}, image {index}", page_index + 1))
                        continue
                    import math
                    width, height = page.get_size()
                    if math.ceil(width * 2) * math.ceil(height * 2) > self.options.max_page_pixels:
                        raise ValueError("PDF page exceeds max_page_pixels")
                    bitmap = page.render(scale=2)
                    picture = bitmap.to_pil()
                    try:
                        picture.save(target, format="PNG")
                    finally:
                        picture.close()
                    total_bytes += target.stat().st_size
                    if total_bytes > self.options.max_uncompressed_bytes:
                        raise ValueError("Rendered PDF exceeds media budget")
                    extracted.append(ExtractedImage(target, f"Rendered PDF page {page_index + 1}", page_index + 1))
                finally:
                    if bitmap is not None:
                        bitmap.close()
                    page.close()
        finally:
            document.close()
        return tuple(extracted)
