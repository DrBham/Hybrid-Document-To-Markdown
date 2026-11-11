"""Explicit, bounded conversion policies shared by the local engine."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ConversionOptions:
    encoding: str = "utf-8-sig"
    text_mode: str = "preserve"
    csv_delimiter: str | None = None
    pdf_mode: str = "pages"
    pdf_columns: int = 1
    spreadsheet_view: str = "formula"
    sheets: tuple[str, ...] = ()
    max_archive_entries: int = 10000
    max_uncompressed_bytes: int = 256 * 1024 * 1024
    max_output_bytes: int = 128 * 1024 * 1024
    max_pdf_pages: int = 500
    max_page_pixels: int = 20_000_000
    max_cells: int = 250_000

    def __post_init__(self):
        if self.text_mode not in {"preserve", "prose"}:
            raise ValueError("text_mode must be preserve or prose")
        if self.pdf_mode not in {"pages", "images", "text"}:
            raise ValueError("pdf_mode must be pages, images or text")
        if self.pdf_columns not in {1, 2}:
            raise ValueError("pdf_columns must be 1 or 2")
        if self.csv_delimiter is not None and len(self.csv_delimiter) != 1:
            raise ValueError("csv_delimiter must be one character")
        if self.spreadsheet_view not in {"formula", "cached"}:
            raise ValueError("spreadsheet_view must be formula or cached")
        for name in ("max_archive_entries", "max_uncompressed_bytes", "max_output_bytes",
                     "max_pdf_pages", "max_page_pixels", "max_cells"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
