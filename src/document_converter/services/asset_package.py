"""Portable ZIP export of Markdown and deduplicated embedded assets."""
import base64
import hashlib
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED


def rewrite_image_uris(markdown, replace_uri):
    """Rewrite generated image syntax, preserving fenced/inline code examples."""
    uri = r"data:image/(?:png|jpeg|gif|webp|bmp|tiff|svg\+xml);base64,[A-Za-z0-9+/=]+"
    patterns = [
        re.compile(r"(!\[(?:\\.|[^\]\\\r\n])*\]\()(?P<uri>" + uri + r")\)"),
        re.compile(r"^ {0,3}\[[^\]\r\n]+\]:[ \t]*(?P<uri>" + uri + r")(?=[ \t]*$)", re.M),
        re.compile(r"<img\b[^>]*?\bsrc=(?P<quote>[\"'])(?P<uri>" + uri + r")(?P=quote)", re.I),
    ]
    def rewrite(segment):
        for pattern in patterns:
            def substitute(match):
                start, end = match.span("uri")
                return match.group()[:start - match.start()] + replace_uri(match.group("uri")) + match.group()[end - match.start():]
            segment = pattern.sub(substitute, segment)
        return segment
    output = []
    fence = None
    for line in markdown.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence is not None:
            output.append(line)
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = marker[1]
            output.append(line)
            continue
        if line.startswith(("    ", "\t")):
            output.append(line)
            continue
        position = 0
        for code in re.finditer(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)", line):
            output.append(rewrite(line[position:code.start()]))
            output.append(code.group())
            position = code.end()
        output.append(rewrite(line[position:]))
    return "".join(output)


class AssetPackageExporter:
    def export(self, markdown: str, output_path: Path, overwrite: bool = False) -> Path:
        if output_path.suffix.lower() != ".zip":
            raise ValueError("Asset package must have a .zip extension")
        if output_path.exists() and not overwrite:
            raise FileExistsError(output_path)
        temporary = None
        assets = {}
        extensions = {"png": "png", "jpeg": "jpg", "gif": "gif", "webp": "webp",
                      "bmp": "bmp", "tiff": "tiff", "svg+xml": "svg"}
        def replace(uri):
            media, payload = uri.split(";base64,", 1)
            kind = media.lower().removeprefix("data:image/")
            data = base64.b64decode(payload, validate=True)
            name = f"assets/{hashlib.sha256(data).hexdigest()}.{extensions[kind]}"
            assets[name] = data
            return name
        content = rewrite_image_uris(markdown, replace)
        try:
            with NamedTemporaryFile(dir=output_path.parent, prefix=".assets-", suffix=".tmp", delete=False) as file:
                temporary = Path(file.name)
            with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
                archive.writestr("document.md", content.encode("utf-8"))
                for name, data in assets.items():
                    archive.writestr(name, data)
            if overwrite:
                os.replace(temporary, output_path)
            else:
                os.link(temporary, output_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return output_path
