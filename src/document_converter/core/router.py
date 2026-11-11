from pathlib import Path

from .base_converter import BaseConverter
from .models import ConversionResult
from .validator import SUPPORTED_FORMATS, validate_file
from .options import ConversionOptions
from zipfile import ZipFile


class ConverterRouter:
    """Route documents to their registered converters."""

    def __init__(
        self,
        converters: dict[str, BaseConverter] | None = None,
        *, options: ConversionOptions | None = None,
    ):
        self.options = options or ConversionOptions()
        self._default_converters = converters is None
        if converters is None:
            from ..converters.markitdown_converter import MarkItDownConverter
            from ..embedded_media.converter import EmbeddedMediaDocumentConverter

            from ..converters.faithful_converter import FaithfulConverter
            from ..converters.local_html_converter import LocalHtmlConverter
            from ..converters.semantic_office import SemanticOfficeConverter
            from ..converters.layout_pdf import LayoutPdfConverter
            engine = EmbeddedMediaDocumentConverter(MarkItDownConverter(), options=self.options)
            converters = {
                extension: engine
                for extension in SUPPORTED_FORMATS
            }
            for extension in (".txt", ".json", ".xml", ".csv", ".xlsx"):
                converters[extension] = EmbeddedMediaDocumentConverter(FaithfulConverter(self.options), options=self.options)
            for extension in (".html", ".htm"):
                converters[extension] = LocalHtmlConverter(self.options)
            for extension in (".docx", ".pptx"):
                converters[extension] = EmbeddedMediaDocumentConverter(SemanticOfficeConverter(), options=self.options)
            converters[".pdf"] = EmbeddedMediaDocumentConverter(LayoutPdfConverter(self.options), options=self.options)

        self.converters = converters

    def convert(self, file_path: Path) -> ConversionResult:
        validate_file(file_path)

        extension = file_path.suffix.lower()
        if self._default_converters and extension == ".pdf":
            import pypdfium2
            document = pypdfium2.PdfDocument(str(file_path))
            try:
                if len(document) > self.options.max_pdf_pages:
                    raise ValueError("PDF exceeds max_pdf_pages")
            finally:
                document.close()
        if self._default_converters and extension in {".docx", ".pptx", ".xlsx"}:
            with ZipFile(file_path) as archive:
                entries = archive.infolist()
                if len(entries) > self.options.max_archive_entries:
                    raise ValueError("Archive exceeds max_archive_entries")
                if sum(entry.file_size for entry in entries) > self.options.max_uncompressed_bytes:
                    raise ValueError("Archive exceeds max_uncompressed_bytes")
                if any(entry.flag_bits & 1 for entry in entries):
                    raise ValueError("Encrypted archive entries are unsupported")

        if extension not in self.converters:
            raise ValueError(
                f"No converter registered for: {extension}"
            )

        converter = self.converters[extension]

        result = converter.convert(file_path)
        if len(result.markdown.encode("utf-8")) > self.options.max_output_bytes:
            raise ValueError("Markdown exceeds max_output_bytes")
        return result
