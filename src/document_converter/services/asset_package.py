"""Portable ZIP export of Markdown and deduplicated embedded assets."""
import base64
import hashlib
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED


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
        def replace(match):
            kind, payload = match.groups()
            data = base64.b64decode(payload, validate=True)
            name = f"assets/{hashlib.sha256(data).hexdigest()}.{extensions[kind]}"
            assets[name] = data
            return name
        content = re.sub(r"(?<=\()data:image/(png|jpeg|gif|webp|bmp|tiff|svg\+xml);base64,([A-Za-z0-9+/=]+)(?=\))", replace, markdown)
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
