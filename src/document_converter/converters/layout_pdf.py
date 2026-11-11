"""Page-aware PDF text and geometric tables, without speculative cleanup."""
import html
import json

import pdfplumber

from ..core.models import ConversionResult
from ..core.serialization import fenced


class LayoutPdfConverter:
    def __init__(self, options):
        self.options = options

    def convert(self, source):
        sections, warnings = [], []
        has_text = False
        with pdfplumber.open(source) as document:
            for number, page in enumerate(document.pages, 1):
                if number > self.options.max_pdf_pages:
                    raise ValueError("PDF exceeds max_pdf_pages")
                tables = page.find_tables()
                if sum(len(table.cells) for table in tables) > self.options.max_cells:
                    raise ValueError("PDF tables exceed max_cells on a page")
                blocks = []
                for detected in tables:
                    rows = detected.extract()
                    geometry = {"page": number, "bbox": list(detected.bbox),
                                "cells": [list(cell) for cell in detected.cells], "rows": rows}
                    # Geometry and row data preserve relationships even when a
                    # merged cell has no equivalent in a Markdown pipe table.
                    xs = sorted({x for cell in detected.cells for x in (cell[0], cell[2])})
                    ys = sorted({y for cell in detected.cells for y in (cell[1], cell[3])})
                    content = ["<table>"]
                    cell_text = {}
                    for row, values in zip(detected.rows, rows):
                        for cell, value in zip(row.cells, values):
                            if cell is not None:
                                cell_text[cell] = value or ""
                    for top in ys[:-1]:
                        content.append("<tr>")
                        for cell in sorted((c for c in detected.cells if c[1] == top), key=lambda c: c[0]):
                            x0, y0, x1, y1 = cell
                            colspan, rowspan = xs.index(x1) - xs.index(x0), ys.index(y1) - ys.index(y0)
                            text = html.escape(cell_text.get(cell, "")).replace("\n", "<br>")
                            content.append(f'<td colspan="{colspan}" rowspan="{rowspan}">{text}</td>')
                        content.append("</tr>")
                    content.append("</table>")
                    content.append("\nTable source geometry:\n\n" + fenced(json.dumps(geometry, ensure_ascii=False), "json"))
                    blocks.append((detected.bbox[1], detected.bbox[0], "\n".join(content)))
                def outside_tables(obj):
                    if obj.get("object_type") != "char":
                        return True
                    x = (obj["x0"] + obj["x1"]) / 2
                    y = (obj["top"] + obj["bottom"]) / 2
                    return not any(b.bbox[0] <= x <= b.bbox[2] and b.bbox[1] <= y <= b.bbox[3] for b in tables)
                text_page = page.filter(outside_tables)
                columns = self.options.pdf_columns
                column_text = []
                page_left, page_top, page_right, page_bottom = page.bbox
                for column in range(columns):
                    left = page_left + (page_right - page_left) * column / columns
                    right = page_left + (page_right - page_left) * (column + 1) / columns
                    region = text_page.crop((left, page_top, right, page_bottom))
                    lines = region.extract_text_lines(layout=False, strip=False)
                    ordered = [(line["top"], line["x0"], line["text"]) for line in lines]
                    ordered += [block for block in blocks if left <= block[1] < right]
                    ordered.sort(key=lambda item: (item[0], item[1]))
                    has_text = has_text or bool(lines) or any(any(value for value in row if value) for table in tables for row in table.extract())
                    column_text.append("\n\n".join(item[2] for item in ordered))
                sections.append(f"## Page {number}\n\n" + "\n\n".join(column_text))
                page.close()
        if not has_text:
            warnings.append("No PDF text layer was extracted. Images are not OCR text.")
        warnings.append("PDF text follows page geometry. Choose pdf_columns=2 only for equal-width two-column pages; irregular layouts require source review.")
        return ConversionResult(source, "pdf", "\n\n".join(sections), tuple(warnings))
