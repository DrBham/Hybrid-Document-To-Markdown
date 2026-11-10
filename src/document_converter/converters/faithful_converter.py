"""Source-preserving paths for text and structured data."""
import csv
import io
import json
from datetime import date, datetime, time
from pathlib import Path

from ..core.models import ConversionResult
from ..core.options import ConversionOptions
from ..core.serialization import fenced, table


class FaithfulConverter:
    def __init__(self, options: ConversionOptions):
        self.options = options

    def convert(self, source: Path) -> ConversionResult:
        suffix = source.suffix.lower()
        if suffix == ".xlsx":
            return self._xlsx(source)
        text = source.read_bytes().decode(self.options.encoding, errors="strict")
        warnings = ()
        if suffix in {".json", ".xml"}:
            markdown = fenced(text, suffix[1:])
        elif suffix == ".csv":
            delimiter = self.options.csv_delimiter
            if delimiter is None:
                try:
                    delimiter = csv.Sniffer().sniff(text[:65536], delimiters=",;\t|").delimiter
                except csv.Error:
                    candidates = []
                    for candidate in ",;\t|":
                        try:
                            sample = list(csv.reader(io.StringIO(text[:65536], newline=""), delimiter=candidate, strict=True))
                        except csv.Error:
                            continue
                        if len(sample) > 1 and len(sample[0]) > 1 and all(len(row) == len(sample[0]) for row in sample):
                            candidates.append(candidate)
                    delimiter = candidates[0] if len(candidates) == 1 else ","
                    if len(candidates) != 1:
                        warnings = ("CSV delimiter could not be inferred; comma was used. Set csv_delimiter explicitly if needed.",)
            rows = []
            count = 0
            for row in csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True):
                count += max(1, len(row))
                if count > self.options.max_cells:
                    raise ValueError("CSV exceeds max_cells")
                rows.append(row)
            markdown = table(rows)
            # Raw source makes quoting, whitespace, and multiline fields recoverable.
            markdown += "\n## Original CSV\n\n" + fenced(text, "csv")
        else:
            markdown = text
        return ConversionResult(source, suffix[1:], markdown, warnings)

    def _xlsx(self, source):
        from openpyxl import load_workbook
        formulas = load_workbook(source, data_only=False, read_only=False)
        cached = None
        warnings = []
        sections = []
        count = 0
        try:
            cached = load_workbook(source, data_only=True, read_only=True)
            missing = set(self.options.sheets) - set(formulas.sheetnames)
            if missing:
                raise ValueError("Requested worksheet is missing: " + ", ".join(sorted(missing)))
            for sheet in formulas:
                if self.options.sheets and sheet.title not in self.options.sheets:
                    continue
                count += sheet.max_row * sheet.max_column
                if count > self.options.max_cells:
                    raise ValueError("Workbook exceeds max_cells; narrow the source data range")
                rows, metadata = [], []
                for row in sheet.iter_rows():
                    values = []
                    for cell in row:
                        value = cell.value
                        display = "" if value is None else (value.isoformat() if isinstance(value, (date, datetime, time)) else str(value))
                        values.append(display)
                        if value is not None:
                            record = {"cell": cell.coordinate, "type": cell.data_type, "value": value,
                                      "number_format": cell.number_format}
                            if cell.hyperlink:
                                record["hyperlink"] = cell.hyperlink.target
                            if cell.data_type == "f":
                                record["cached_value"] = cached[sheet.title][cell.coordinate].value
                                if self.options.spreadsheet_view == "cached":
                                    cached_value = record["cached_value"]
                                    values[-1] = "[cache unavailable]" if cached_value is None else str(cached_value)
                                warnings.append("Formula caches may be absent or stale; formulas were not recalculated.")
                            metadata.append(record)
                    rows.append(values)
                sections.append("## " + sheet.title.replace("\n", " ") + "\n\n" + table(rows))
                sections.append("### Cell metadata\n\n" + fenced(json.dumps({
                    "sheet": sheet.title, "merged_ranges": [str(r) for r in sheet.merged_cells.ranges],
                    "cells": metadata,
                }, ensure_ascii=False, indent=2, default=str), "json"))
        finally:
            formulas.close()
            if cached is not None:
                cached.close()
        return ConversionResult(source, "xlsx", "\n".join(sections), tuple(dict.fromkeys(warnings)))
