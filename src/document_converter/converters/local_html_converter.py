"""Semantic HTML conversion with local assets and untouched pre blocks."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from bs4 import BeautifulSoup
from markitdown.converters._html_converter import HtmlConverter

from ..core.models import ConversionResult
from ..core.serialization import fenced
from ..embedded_media.converter import MIME_TYPES, encode_image_data_uri


class LocalHtmlConverter:
    def __init__(self, options):
        self.options = options

    def convert(self, source: Path):
        soup = BeautifulSoup(source.read_bytes().decode(self.options.encoding), "html.parser")
        warnings, preserved = [], {}
        for node in soup(["script", "style", "iframe", "object"]):
            node.decompose()
        for node in soup.find_all("pre"):
            if node.find_parent("table") is not None:
                continue  # Keep semantic <pre> inside its protected HTML table.
            token = "PRESERVED" + uuid4().hex.upper()
            preserved[token] = fenced(node.get_text(), "")
            node.replace_with(token)
        total = 0
        root = source.resolve().parent
        for node in soup.find_all("img"):
            address = str(node.get("src", ""))
            parsed = urlsplit(address)
            if parsed.scheme or parsed.netloc:
                warnings.append("External or inline HTML image was not fetched or repackaged.")
                if parsed.scheme not in {"http", "https", "data"}:
                    del node["src"]
                continue
            candidate = (root / unquote(parsed.path)).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file() or candidate.suffix.lower() not in MIME_TYPES:
                warnings.append("Local HTML image is missing, unsupported, or outside the document folder.")
                continue
            total += candidate.stat().st_size
            if total > self.options.max_uncompressed_bytes or (total * 4 + 2) // 3 > self.options.max_output_bytes:
                raise ValueError("HTML assets exceed media budget")
            node["src"] = encode_image_data_uri(candidate)
        for node in soup.find_all("a", href=True):
            address = str(node["href"])
            scheme = urlsplit(address).scheme.lower()
            if scheme and scheme not in {"https", "http", "mailto"}:
                del node["href"]
                warnings.append("Unsupported link scheme removed.")
            elif not scheme and not address.startswith("#"):
                warnings.append("Relative document links require their original companion files.")
        for node in list(soup.find_all("table")):
            if node.find_parent("table") is not None:
                continue
            if node.find(["td", "th"], attrs={"colspan": True}) or node.find(["td", "th"], attrs={"rowspan": True}) or node.find("table") or node.find("pre"):
                token = "PRESERVEDTABLE" + uuid4().hex.upper()
                preserved[token] = str(node)
                node.replace_with(token)
                warnings.append("Complex table preserved as HTML to retain cell spans and nesting.")
        markdown = HtmlConverter().convert_string(str(soup), keep_data_uris=True).markdown
        for token, block in reversed(list(preserved.items())):
            markdown = markdown.replace(token, "\n\n" + block + "\n")
        return ConversionResult(source, source.suffix[1:], markdown, tuple(dict.fromkeys(warnings)))
