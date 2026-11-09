from pathlib import Path

from .base_converter import BaseConverter
from .models import ConversionResult
from .validator import SUPPORTED_FORMATS, validate_file


class ConverterRouter:
    """Route documents to their registered converters."""

    def __init__(
        self,
        converters: dict[str, BaseConverter] | None = None,
    ):
        if converters is None:
            from ..converters.markitdown_converter import MarkItDownConverter
            from ..embedded_media.converter import EmbeddedMediaDocumentConverter

            engine = EmbeddedMediaDocumentConverter(MarkItDownConverter())
            converters = {
                extension: engine
                for extension in SUPPORTED_FORMATS
            }

        self.converters = converters

    def convert(self, file_path: Path) -> ConversionResult:
        validate_file(file_path)

        extension = file_path.suffix.lower()

        if extension not in self.converters:
            raise ValueError(
                f"No converter registered for: {extension}"
            )

        converter = self.converters[extension]

        return converter.convert(file_path)
