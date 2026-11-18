"""Page-aware PDF text and geometric tables, without speculative cleanup."""

from __future__ import annotations

from dataclasses import dataclass, field
import html
import json
from uuid import uuid4

import pdfplumber

from ..core.models import ConversionResult, PageMediaSlot
from ..core.serialization import fenced, metadata_section


@dataclass
class _Cell:
    text: str
    colspan: int = 1
    rowspan: int = 1


@dataclass
class _TableBlock:
    page: int
    page_height: float
    bbox: tuple[float, float, float, float]
    columns: tuple[float, ...]
    rows: list[list[_Cell]]
    geometry: dict
    repair_count: int = 0
    suppressed: bool = False
    merged_into: _TableBlock | None = None
    segments: list[dict] = field(default_factory=list)

    def root(self) -> _TableBlock:
        return self.merged_into.root() if self.merged_into is not None else self


@dataclass
class _PageRecord:
    number: int
    columns: list[list[tuple[float, float, str | _TableBlock]]]
    tables: list[_TableBlock]
    media_token: str | None


def _repair_cell_text(value: str) -> tuple[str, int]:
    """Repair line wraps that split one structured token inside a table cell."""
    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(lines) < 2:
        return value, 0
    repaired = lines[0]
    changes = 0
    for right in lines[1:]:
        left = repaired.rstrip()
        right_stripped = right.lstrip()
        if not left or not right_stripped:
            repaired += "\n" + right
            continue
        left_char, right_char = left[-1], right_stripped[0]
        digit_fragment = left_char.isdigit() and right_char.isdigit()
        punctuation_fragment = (
            left_char in "._:@=-{[("
            or right_char in "._:@=,;)]}"
            or (left_char == "/" and len(left) > 1 and not left[-2].isspace())
        )
        if digit_fragment or punctuation_fragment:
            repaired = left + right_stripped
            changes += 1
        else:
            repaired += "\n" + right
    return repaired, changes


def _same_columns(first: _TableBlock, second: _TableBlock) -> bool:
    return len(first.columns) == len(second.columns) and all(
        abs(left - right) <= 3.0
        for left, right in zip(first.columns, second.columns)
    )


def _row_text(row: list[_Cell]) -> tuple[str, ...]:
    return tuple(" ".join(cell.text.split()).casefold() for cell in row)


def _repeated_header(first: _TableBlock, second: _TableBlock) -> bool:
    if not first.root().rows or not second.rows:
        return False
    original = _row_text(first.root().rows[0])
    candidate = _row_text(second.rows[0])
    return bool(original) and original == candidate and any(original)


def _continuation_row(previous: list[_Cell], current: list[_Cell]) -> bool:
    if len(previous) != len(current):
        return False
    previous_text = [cell.text.strip() for cell in previous]
    current_text = [cell.text.strip() for cell in current]
    if current_text and not current_text[0] and any(current_text[1:]):
        return True
    return any(
        left and right and left.rstrip().endswith(("/", "-", "_", ":", ","))
        for left, right in zip(previous_text, current_text)
    ) and any(not value for value in current_text)


def _join_fragments(left: str, right: str) -> str:
    left, right = left.rstrip(), right.lstrip()
    if not left:
        return right
    if not right:
        return left
    repaired, changes = _repair_cell_text(left + "\n" + right)
    return repaired if changes else left + " " + right


def _merge_table(root: _TableBlock, continuation: _TableBlock) -> None:
    if root.rows and continuation.rows and _continuation_row(
        root.rows[-1], continuation.rows[0]
    ):
        previous = root.rows[-1]
        current = continuation.rows.pop(0)
        for left, right in zip(previous, current):
            left.text = _join_fragments(left.text, right.text)
    root.rows.extend(continuation.rows)
    root.segments.append(continuation.geometry)
    root.repair_count += continuation.repair_count
    continuation.suppressed = True
    continuation.merged_into = root


def _stitch_continued_tables(pages: list[_PageRecord]) -> int:
    joined = 0
    for previous_page, current_page in zip(pages, pages[1:]):
        if not previous_page.tables or not current_page.tables:
            continue
        previous = previous_page.tables[-1]
        current = current_page.tables[0]
        if (
            previous.bbox[3] < previous.page_height * 0.80
            or current.bbox[1] > current.page_height * 0.20
            or not _same_columns(previous, current)
            or _repeated_header(previous, current)
        ):
            continue
        _merge_table(previous.root(), current)
        joined += 1
    return joined


def _render_table(table: _TableBlock, metadata_mode: str) -> str:
    content = ["<table>"]
    for row in table.rows:
        content.append("<tr>")
        for cell in row:
            text = html.escape(cell.text).replace("\n", "<br>")
            content.append(
                f'<td colspan="{cell.colspan}" rowspan="{cell.rowspan}">{text}</td>'
            )
        content.append("</tr>")
    content.append("</table>")
    if metadata_mode == "embedded":
        geometry = table.geometry if len(table.segments) == 1 else {
            "pages": [segment["page"] for segment in table.segments],
            "segments": table.segments,
        }
        content.append(metadata_section(
            "Table source geometry",
            fenced(json.dumps(geometry, ensure_ascii=False), "json"),
            "pdf-table-geometry",
        ))
    return "\n".join(content)


class LayoutPdfConverter:
    def __init__(self, options):
        self.options = options

    def convert(self, source):
        warnings: list[str] = []
        media_slots: list[PageMediaSlot] = []
        pages: list[_PageRecord] = []
        has_text = False
        with pdfplumber.open(source) as document:
            for number, page in enumerate(document.pages, 1):
                if number > self.options.max_pdf_pages:
                    raise ValueError("PDF exceeds max_pdf_pages")
                detected_tables = page.find_tables()
                if sum(len(table.cells) for table in detected_tables) > self.options.max_cells:
                    raise ValueError("PDF tables exceed max_cells on a page")

                table_blocks: list[_TableBlock] = []
                for detected in detected_tables:
                    raw_rows = detected.extract()
                    repaired_rows: list[list[str]] = []
                    repair_count = 0
                    for row in raw_rows:
                        repaired_row = []
                        for value in row:
                            repaired, changes = _repair_cell_text(value or "")
                            repaired_row.append(repaired)
                            repair_count += changes
                        repaired_rows.append(repaired_row)

                    xs = sorted({value for cell in detected.cells for value in (cell[0], cell[2])})
                    ys = sorted({value for cell in detected.cells for value in (cell[1], cell[3])})
                    rows: list[list[_Cell]] = []
                    for detected_row, values in zip(detected.rows, repaired_rows):
                        cells = []
                        for cell, value in zip(detected_row.cells, values):
                            if cell is None:
                                continue
                            x0, y0, x1, y1 = cell
                            cells.append(_Cell(
                                value,
                                xs.index(x1) - xs.index(x0),
                                ys.index(y1) - ys.index(y0),
                            ))
                        rows.append(cells)

                    geometry = {
                        "page": number,
                        "bbox": list(detected.bbox),
                        "cells": [list(cell) for cell in detected.cells],
                        "rows": repaired_rows,
                    }
                    if repair_count:
                        geometry["raw_rows"] = raw_rows
                    table_blocks.append(_TableBlock(
                        page=number,
                        page_height=page.height,
                        bbox=tuple(detected.bbox),
                        columns=tuple(xs),
                        rows=rows,
                        geometry=geometry,
                        repair_count=repair_count,
                        segments=[geometry],
                    ))

                def outside_tables(obj):
                    if obj.get("object_type") != "char":
                        return True
                    x = (obj["x0"] + obj["x1"]) / 2
                    y = (obj["top"] + obj["bottom"]) / 2
                    return not any(
                        table.bbox[0] <= x <= table.bbox[2]
                        and table.bbox[1] <= y <= table.bbox[3]
                        for table in detected_tables
                    )

                text_page = page.filter(outside_tables)
                page_columns: list[list[tuple[float, float, str | _TableBlock]]] = []
                page_left, page_top, page_right, page_bottom = page.bbox
                for column in range(self.options.pdf_columns):
                    left = page_left + (page_right - page_left) * column / self.options.pdf_columns
                    right = page_left + (page_right - page_left) * (column + 1) / self.options.pdf_columns
                    region = text_page.crop((left, page_top, right, page_bottom))
                    lines = region.extract_text_lines(layout=False, strip=False)
                    ordered: list[tuple[float, float, str | _TableBlock]] = [
                        (line["top"], line["x0"], line["text"]) for line in lines
                    ]
                    ordered.extend(
                        (table.bbox[1], table.bbox[0], table)
                        for table in table_blocks
                        if left <= table.bbox[0] < right
                    )
                    ordered.sort(key=lambda item: (item[0], item[1]))
                    page_columns.append(ordered)

                has_text = has_text or bool(text_page.chars) or any(
                    cell.text
                    for table in table_blocks
                    for row in table.rows
                    for cell in row
                )
                token = None
                if self.options.pdf_mode != "text":
                    token = "HYBRIDPAGE" + uuid4().hex.upper()
                    media_slots.append(PageMediaSlot(token, number))
                pages.append(_PageRecord(number, page_columns, table_blocks, token))
                page.close()

        joined = _stitch_continued_tables(pages)
        repaired = sum(
            table.repair_count
            for page in pages
            for table in page.tables
            if not table.suppressed
        )
        if repaired:
            warnings.append(
                f"Repaired {repaired} structured token wrap(s) inside PDF table cells; "
                "verify source values."
            )
        if joined:
            warnings.append(
                f"Joined table continuations across {joined} PDF page "
                "boundary/boundaries using matching column geometry."
            )

        sections: list[str] = []
        for page in pages:
            rendered_columns = []
            for column in page.columns:
                blocks = []
                for _top, _left, item in column:
                    if isinstance(item, _TableBlock):
                        if item.suppressed:
                            continue
                        blocks.append(_render_table(item, self.options.metadata_mode))
                    else:
                        blocks.append(item)
                rendered_columns.append("\n\n".join(blocks))
            sections.append(f"## Page {page.number}\n\n" + "\n\n".join(rendered_columns))
            if page.media_token is not None:
                sections.append(page.media_token)

        if not has_text:
            warnings.append("No PDF text layer was extracted. Images are not OCR text.")
        warnings.append(
            "PDF text follows page geometry. Choose pdf_columns=2 only for equal-width "
            "two-column pages; irregular layouts require source review."
        )
        return ConversionResult(
            source,
            "pdf",
            "\n\n".join(sections),
            tuple(warnings),
            page_media_slots=tuple(media_slots),
        )
