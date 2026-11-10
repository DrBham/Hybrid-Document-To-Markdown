
from pathlib import Path
import os
from tempfile import NamedTemporaryFile


class MarkdownExporter:
    """Export Markdown content with overwrite protection."""

    def export(
        self,
        markdown: str,
        output_path: Path,
        overwrite: bool = False,
    ) -> Path:
        if output_path.suffix.lower() != ".md":
            raise ValueError(
                "Output file must have a .md extension"
            )

        if output_path.exists() and not overwrite:
            raise FileExistsError(
                f"Output file already exists: {output_path}"
            )

        temporary = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                    dir=output_path.parent, prefix=".markdown-", suffix=".tmp",
                                    delete=False) as file:
                temporary = Path(file.name)
                file.write(markdown)
                file.flush()
                os.fsync(file.fileno())
            if overwrite:
                os.replace(temporary, output_path)
            else:
                # Publishing a hard link fails atomically if another writer wins.
                os.link(temporary, output_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

        return output_path
