"""Semantic Word output and source-backed PowerPoint structures."""
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from dataclasses import replace

import mammoth
from bs4 import BeautifulSoup, NavigableString
from markitdown.converters._html_converter import HtmlConverter

from ..core.models import ConversionResult
from ..core.options import ConversionOptions
from ..core.serialization import metadata_section
from ..embedded_media.placement import ImageCollector
from .docx_structure import HEADING_STYLE_MAP, analyze_docx, restore_structure
from .office_structure import presentation_structure


def _promote_header_row(table):
    """Use a simple Word table's first row as its Markdown header.

    Without <th>, the Markdown table writer invents an empty header row and
    demotes the real header to data.
    """
    if table.find("th") is not None or table.find("table") is not None:
        return
    first = table.find("tr")
    if first is None:
        return
    for cell in first.find_all("td", recursive=False):
        cell.name = "th"
        # Header cells are already emphasized; drop bold that wraps the whole cell.
        for strong in cell.find_all(["strong", "b"]):
            if strong.get_text(strip=True) == cell.get_text(strip=True):
                strong.unwrap()


class SemanticOfficeConverter:
    def __init__(self, options: ConversionOptions | None = None):
        self.options = options or ConversionOptions()

    def convert(self, source: Path):
        images = ImageCollector()
        if source.suffix.lower() == ".pptx":
            from markitdown.converters._pptx_converter import PptxConverter
            from markitdown import StreamInfo

            class PositionedPptx(PptxConverter):
                def _convert_picture_to_markdown(self, shape, **kwargs):
                    data, mime, filename = self._get_image_info(shape)
                    if data is None:
                        return "\n[Image unavailable in source]\n"
                    alt = shape._element._nvXxPr.cNvPr.get("descr") or shape.name
                    return "\n" + images.add(data, mime or "image/png", alt) + "\n"

            with source.open("rb") as stream:
                converted = PositionedPptx().convert(stream, StreamInfo(extension=".pptx"))
            result = ConversionResult(source, "pptx", converted.markdown, inline_images=tuple(images.images))
            if self.options.metadata_mode == "embedded":
                result.markdown += "\n\n" + metadata_section(
                    "Presentation source structure",
                    presentation_structure(source),
                    "presentation-structure",
                )
                result.warnings += ("Presentation topology and chart source data are preserved in the source-structure appendix; spatial relationships are not inferred.",)
            return result
        @mammoth.images.img_element
        def collect_image(image):
            with image.open() as stream:
                data = stream.read()
            return {"src": images.add(data, image.content_type, image.alt_text or "Word document image")}

        structure = analyze_docx(source.read_bytes())
        with (BytesIO(structure.package) if structure.package else source.open("rb")) as stream:
            result = mammoth.convert_to_html(stream, style_map=HEADING_STYLE_MAP, include_embedded_style_map=False, convert_image=collect_image)
        soup = BeautifulSoup(result.value, "html.parser")
        # Markdown writers drop whitespace-only emphasis, which glues adjacent words.
        for node in soup.find_all(["strong", "em", "b", "i", "u", "s", "sup", "sub"]):
            if node.parent is not None and not node.find("img") and node.get_text() and not node.get_text().strip():
                node.replace_with(NavigableString(node.get_text()))
        for index, item in enumerate(images.images):
            node = soup.find("img", src=item.token)
            if node is not None:
                images.images[index] = replace(item, html=node.find_parent("table") is not None)
                node.replace_with(item.token)
        protected = {}
        for node in soup.find_all(id=lambda value: value and value.startswith(("footnote-ref-", "endnote-ref-"))):
            if node.parent.name == "sup":
                node = node.parent
            token = "OFFICEREFERENCE" + uuid4().hex.upper()
            protected[token] = str(node)
            node.replace_with(token)
        # Retain spans, nested tables, and footnote anchor IDs as semantic HTML.
        for node in list(soup.find_all("table")) + list(soup.find_all("ol")):
            if node.parent is None:
                continue
            complex_table = node.name == "table" and (node.find(["td", "th"], attrs={"colspan": True}) or node.find(["td", "th"], attrs={"rowspan": True}) or node.find("table"))
            footnotes = node.name == "ol" and node.find(id=lambda value: value and value.startswith(("footnote-", "endnote-")))
            if complex_table or footnotes:
                token = "OFFICEBLOCK" + uuid4().hex.upper()
                protected[token] = str(node)
                node.replace_with(token)
        for table in soup.find_all("table"):
            _promote_header_row(table)
        markdown = HtmlConverter().convert_string(str(soup)).markdown
        # Restore outer blocks before reference tokens captured inside them.
        for token, html in reversed(list(protected.items())):
            markdown = markdown.replace(token, html if token.startswith("OFFICEREFERENCE") else "\n\n" + html + "\n\n")
        markdown = restore_structure(markdown, structure)
        # Synthetic heading styles are internal and intentionally absent from styles.xml.
        # Synthetic heading styles are internal. Unmapped Word style names only
        # mean "rendered as a normal paragraph/run"; they are not content loss.
        warnings = tuple(dict.fromkeys(
            message.message for message in result.messages
            if "HDMHeading" not in message.message
            and not message.message.startswith(("Unrecognised paragraph style", "Unrecognised run style"))
        )) + structure.warnings
        if protected:
            warnings += ("Complex tables/notes use semantic HTML to retain merged cells and reference anchors.",)
        return ConversionResult(source, "docx", markdown, warnings, inline_images=tuple(images.images))
