"""Preserve source structure that cannot be represented by flat Markdown."""
import json
import posixpath
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from ..core.serialization import fenced


def parse_xml(data):
    probe = data.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
        raise ValueError("DTD/entity declarations are unsupported in Office XML")
    return ET.fromstring(data)


def worksheet_values(source):
    """Read literal <v> text before numeric coercion by openpyxl."""
    main = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    relation = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with ZipFile(source) as archive:
        workbook = parse_xml(archive.read("xl/workbook.xml"))
        rels = parse_xml(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels if r.get("TargetMode") != "External"}
        values = {}
        for sheet in workbook.findall(f"{main}sheets/{main}sheet"):
            target = targets[sheet.get(relation)]
            part = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            root = parse_xml(archive.read(part))
            values[sheet.get("name")] = {
                cell.get("r"): {"xml_value": cell.findtext(main + "v"),
                                "xml_type": cell.get("t", "n"),
                                "xml_formula": cell.findtext(main + "f")}
                for cell in root.iter(main + "c")
            }
        return values


def presentation_structure(source):
    """Expose actual shape/connector IDs and chart/diagram source parts.

    IDs express topology when present. We never infer a relationship from
    proximity or claim that this is a visual interpretation of the diagram.
    """
    with ZipFile(source) as archive:
        presentation = parse_xml(archive.read("ppt/presentation.xml"))
        rels = parse_xml(archive.read("ppt/_rels/presentation.xml.rels"))
        lookup = {r.get("Id"): r.get("Target") for r in rels if r.get("TargetMode") != "External"}
        ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
              "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        relation = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        records = []
        for index, slide in enumerate(presentation.findall("p:sldIdLst/p:sldId", ns), 1):
            target = lookup[slide.get(relation)]
            part = target.lstrip("/") if target.startswith("/") else posixpath.normpath("ppt/" + target)
            root = parse_xml(archive.read(part))
            shapes = []
            for shape in root.findall(".//p:spTree/*", ns):
                ids = shape.findall(".//p:cNvPr", ns)
                if not ids:
                    continue
                shapes.append({"id": ids[0].get("id"), "name": ids[0].get("name"),
                               "kind": shape.tag.rsplit("}", 1)[-1],
                               "text": [n.text or "" for n in shape.findall(".//a:t", ns)],
                               "connections": [{"endpoint": n.tag.rsplit("}", 1)[-1], **n.attrib}
                                               for n in shape.iter() if n.tag in {"{" + ns["a"] + "}stCxn", "{" + ns["a"] + "}endCxn"}]})
            records.append({"slide": index, "part": part, "shapes": shapes})
        sections = ["## Presentation source structure\n\n" + fenced(json.dumps(records, ensure_ascii=False, indent=2), "json")]
        for name in sorted(archive.namelist()):
            if name.startswith(("ppt/charts/chart", "ppt/diagrams/data")) and name.endswith(".xml"):
                data = archive.read(name)
                parse_xml(data)
                sections.append("### " + name + "\n\n" + fenced(data.decode("utf-8-sig"), "xml"))
        return "\n".join(sections)
