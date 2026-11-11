"""Semantic Word output and source-backed PowerPoint structures."""
from pathlib import Path
from uuid import uuid4

import mammoth
from bs4 import BeautifulSoup
from markitdown.converters._html_converter import HtmlConverter

from ..core.models import ConversionResult
from .markitdown_converter import MarkItDownConverter
from .office_structure import presentation_structure


class SemanticOfficeConverter:
    def convert(self, source: Path):
        if source.suffix.lower() == ".pptx":
            result = MarkItDownConverter().convert(source)
            result.markdown += "\n\n" + presentation_structure(source)
            result.warnings += ("Presentation topology and chart source data are preserved in the source-structure appendix; spatial relationships are not inferred.",)
            return result
        with source.open("rb") as stream:
            result = mammoth.convert_to_html(stream, include_embedded_style_map=False)
        soup = BeautifulSoup(result.value, "html.parser")
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
        markdown = HtmlConverter().convert_string(str(soup)).markdown
        # Restore outer blocks before reference tokens captured inside them.
        for token, html in reversed(list(protected.items())):
            markdown = markdown.replace(token, html if token.startswith("OFFICEREFERENCE") else "\n\n" + html + "\n\n")
        warnings = tuple(dict.fromkeys(message.message for message in result.messages))
        if protected:
            warnings += ("Complex tables/notes use semantic HTML to retain merged cells and reference anchors.",)
        return ConversionResult(source, "docx", markdown, warnings)
