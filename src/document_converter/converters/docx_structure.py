"""Expose Word structure that Mammoth drops: OMML equations and list labels.

The source package is rewritten in memory only. Each equation and numbered
paragraph receives an opaque token; the Markdown pass replaces the tokens after
HTML-to-Markdown conversion so LaTeX and labels are never escaped.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
TOKEN = re.compile(r"HDM(?:LIST|MATH)[0-9A-F]{32}")
NATIVE_ORDERED = re.compile(r"\d{1,9}[.)]")


def w(tag):
    return f"{{{W}}}{tag}"


def m(tag):
    return f"{{{M}}}{tag}"


def _parse(data):
    probe = data.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
        raise ValueError("DTD/entity declarations are unsupported in Office XML")
    parser = etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False)
    return etree.fromstring(data, parser)


def _val(node, default=None):
    return default if node is None else node.get(w("val"), default)


@dataclass(frozen=True)
class _Level:
    start: int
    fmt: str
    text: str
    restart: int | None
    legal: bool


def _level(node):
    restart = node.find(w("lvlRestart"))
    return _Level(
        start=int(_val(node.find(w("start")), "0")),
        fmt=_val(node.find(w("numFmt")), "decimal"),
        text=_val(node.find(w("lvlText")), ""),
        restart=None if restart is None else int(_val(restart, "1")),
        legal=node.find(w("isLgl")) is not None and _val(node.find(w("isLgl")), "1") not in {"0", "false"},
    )


def _letters(value):
    if value < 1:
        return str(value)
    # Word repeats the letter after z: a..z, aa..zz, aaa..
    return chr(ord("a") + (value - 1) % 26) * ((value - 1) // 26 + 1)


def _roman(value):
    if not 0 < value < 4000:
        return str(value)
    result = ""
    for number, numeral in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
                            (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        count, value = divmod(value, number)
        result += numeral * count
    return result


def _format(value, fmt):
    if fmt == "lowerLetter":
        return _letters(value)
    if fmt == "upperLetter":
        return _letters(value).upper()
    if fmt == "lowerRoman":
        return _roman(value)
    if fmt == "upperRoman":
        return _roman(value).upper()
    if fmt == "decimalZero":
        return f"{value:02d}"
    if fmt == "ordinal":
        suffix = "th" if 10 <= value % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
        return f"{value}{suffix}"
    return str(value)


class _Numbering:
    """Simulate Word list counters in document order."""

    def __init__(self, root):
        abstract = {}
        if root is not None:
            for node in root.findall(w("abstractNum")):
                abstract[node.get(w("abstractNumId"))] = {int(level.get(w("ilvl"), "0")): _level(level)
                                                          for level in node.findall(w("lvl"))}
        self.nums = {}
        if root is not None:
            for node in root.findall(w("num")):
                abstract_id = _val(node.find(w("abstractNumId")))
                levels = dict(abstract.get(abstract_id, {}))
                starts = {}
                for override in node.findall(w("lvlOverride")):
                    index = int(override.get(w("ilvl"), "0"))
                    if override.find(w("lvl")) is not None:
                        levels[index] = _level(override.find(w("lvl")))
                    if override.find(w("startOverride")) is not None:
                        starts[index] = int(_val(override.find(w("startOverride")), "0"))
                self.nums[node.get(w("numId"))] = (abstract_id, levels, starts)
        self.counters = {}
        self.pending = {}
        self.seen = set()

    def next(self, num_id, ilvl):
        entry = self.nums.get(num_id)
        if entry is None or ilvl not in entry[1]:
            return None
        abstract_id, levels, starts = entry
        counters = self.counters.setdefault(abstract_id, {})
        pending = self.pending.setdefault(abstract_id, {})
        if num_id not in self.seen:
            # A new list instance with startOverride restarts the shared abstract list.
            self.seen.add(num_id)
            for index, start in starts.items():
                for level in [key for key in counters if key >= index]:
                    del counters[level]
                pending[index] = start
        level = levels[ilvl]
        if ilvl in counters:
            counters[ilvl] += 1
        else:
            counters[ilvl] = pending.pop(ilvl, level.start)
        for deeper in [key for key in counters if key > ilvl]:
            restart = levels[deeper].restart if deeper in levels else None
            if restart is None or (restart != 0 and ilvl < restart):
                del counters[deeper]
        if level.fmt == "bullet":
            return "bullet", ""
        if level.fmt == "none" or not level.text:
            return "none", ""

        def substitute(match):
            index = int(match.group(1)) - 1
            source = levels.get(index)
            value = counters.get(index, source.start if source else 1)
            return str(value) if level.legal or source is None else _format(value, source.fmt)

        return "ordered", re.sub(r"%([1-9])", substitute, level.text).strip()


@dataclass
class DocxStructure:
    """Rewritten package plus the token values to restore after Markdown conversion."""

    package: bytes | None = None
    lists: dict = field(default_factory=dict)
    math: dict = field(default_factory=dict)
    warnings: tuple = ()


class _Styles:
    """Style lookups that follow basedOn chains."""

    def __init__(self, root):
        self.nodes = {}
        for style in ([] if root is None else root.findall(w("style"))):
            self.nodes[(style.get(w("type")), style.get(w("styleId")))] = style

    def chain(self, kind, style_id):
        for _ in range(20):
            style = self.nodes.get((kind, style_id))
            if style is None:
                return
            yield style
            style_id = _val(style.find(w("basedOn")))

    def name(self, style_id):
        style = self.nodes.get(("paragraph", style_id))
        return "" if style is None else (_val(style.find(w("name")), "") or "").lower()

    def numbering(self, style_id):
        for style in self.chain("paragraph", style_id):
            num = style.find(f"{w('pPr')}/{w('numPr')}")
            if num is not None and num.find(w("numId")) is not None:
                return _val(num.find(w("numId"))), _val(num.find(w("ilvl")))
        return None, None

    def outline(self, style_id):
        for style in self.chain("paragraph", style_id):
            node = style.find(f"{w('pPr')}/{w('outlineLvl')}")
            if node is not None:
                return int(_val(node, "9"))
        return None

    def bold(self, kind, style_id):
        for style in self.chain(kind, style_id):
            node = style.find(f"{w('rPr')}/{w('b')}")
            if node is not None:
                return _on(node)
        return None


def _on(node):
    return _val(node, "1") not in {"0", "false", "off"}


WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
CAPTION = re.compile(r"^\s*[^\W\d_]{2,20}\.?\s+(?:\d+|[IVXLC]+)(?:[.\-–]\d+)*\s*[.:\-–]", re.I)
NUMERIC_LABEL = re.compile(r"\d+(?:\.\d+)*\.?")


def _texts(paragraph):
    return [node for node in paragraph.iter(w("t")) if not TOKEN.fullmatch(node.text or "")]


def _paragraph_text(paragraph):
    return re.sub(r"\s+", " ", "".join(node.text or "" for node in _texts(paragraph))).strip()


def _run_bold(run, paragraph_style, styles):
    properties = run.find(w("rPr"))
    if properties is not None:
        if properties.find(w("b")) is not None:
            return _on(properties.find(w("b")))
        character = _val(properties.find(w("rStyle")))
        if character and styles.bold("character", character) is not None:
            return styles.bold("character", character)
    return bool(styles.bold("paragraph", paragraph_style))


def _fully_bold(paragraph, paragraph_style, styles):
    runs = [node.getparent() for node in _texts(paragraph) if (node.text or "").strip()]
    return bool(runs) and all(run.tag == w("r") and _run_bold(run, paragraph_style, styles) for run in runs)


def _meaningful_alt(text):
    """Reject empty alt text and short mixed-script noise from broken encoders."""
    counts = {}
    for character in (text or "").strip():
        if unicodedata.category(character) in {"Cn", "Co", "Cs"}:
            return False
        if character.isalnum():
            try:
                script = unicodedata.name(character).split()[0]
            except ValueError:
                return False
            counts[script] = counts.get(script, 0) + 1
    return max(counts.values(), default=0) >= 2


def _is_caption(paragraph, styles):
    properties = paragraph.find(w("pPr"))
    style = None if properties is None else _val(properties.find(w("pStyle")))
    if "caption" in styles.name(style) or "caption" in (style or "").lower():
        return True
    fields = [node.text or "" for node in paragraph.iter(w("instrText"))] + \
             [node.get(w("instr"), "") for node in paragraph.iter(w("fldSimple"))]
    return any(re.match(r"\s*SEQ\b", field) for field in fields) or bool(CAPTION.match(_paragraph_text(paragraph)))


def _nearby_caption(paragraph, styles):
    """Nearest caption: the image paragraph, then up to two text paragraphs after, then before."""
    candidates = [paragraph]
    for preceding in (False, True):
        found = 0
        for sibling in paragraph.itersiblings(preceding=preceding):
            if sibling.tag != w("p"):
                break
            if _paragraph_text(sibling):
                candidates.append(sibling)
                found += 1
                if found == 2:
                    break
    for candidate in candidates:
        text = _paragraph_text(candidate)
        if text and _is_caption(candidate, styles):
            return text[:250]
    return None


def _heading_level(paragraph, label, styles):
    """Infer Markdown heading levels for Word documents without heading styles."""
    properties = paragraph.find(w("pPr"))
    style = None if properties is None else _val(properties.find(w("pStyle")))
    name = styles.name(style)
    if re.fullmatch(r"heading [1-9]", name):
        return None  # Mammoth already maps built-in headings.
    text = _paragraph_text(paragraph)
    if not text:
        return None
    outline = None if properties is None else properties.find(w("outlineLvl"))
    outline = int(_val(outline, "9")) if outline is not None else styles.outline(style)
    if outline is not None and 0 <= outline <= 5:
        return outline + 1
    if len(text) > 120 or len(text.split()) > 12 or text.endswith((".", ":", ";", ",")):
        return None
    title = name == "title"
    emphasized = title or _fully_bold(paragraph, style, styles)
    if label and NUMERIC_LABEL.fullmatch(label) and emphasized:
        depth = len(label.rstrip(".").split("."))
        if depth > 1 or text.isupper() or title:
            return min(depth + 1, 6)
        return None
    if label:
        return None
    if title:
        return 1
    if emphasized and text.isupper() and len(text.split()) <= 8:
        return 2
    return None


def _strip_bold(paragraph, styles):
    for run in paragraph.iter(w("r")):
        properties = run.find(w("rPr"))
        if properties is None:
            continue
        for node in properties.findall(w("b")) + properties.findall(w("bCs")):
            properties.remove(node)
        character = properties.find(w("rStyle"))
        if character is not None and styles.bold("character", _val(character)):
            properties.remove(character)


def _in(node, tags):
    return any(parent.tag in tags for parent in node.iterancestors())


HEADING_STYLE_MAP = "\n".join(f"p.HDMHeading{level} => h{level}:fresh" for level in range(1, 7))


def _token_run(token):
    run = etree.Element(w("r"))
    text = etree.SubElement(run, w("t"))
    text.set(XML_SPACE, "preserve")
    text.text = token
    return run


def _equation_text(node):
    return "".join(node.itertext()).strip()


def _latex(node):
    from markitdown.converter_utils.docx.math.omml import oMath2Latex
    # The bundled converter expects stdlib ElementTree nodes.
    element = ET.fromstring(etree.tostring(node))
    # OMML may omit property elements that carry only defaults; the converter
    # requires them to exist.
    for name in ("f", "d", "nary", "acc", "bar", "groupChr", "rad", "limLow", "limUpp", "m", "eqArr", "func", "box", "borderBox"):
        for owner in element.iter(m(name)):
            if owner.find(m(name + "Pr")) is None:
                owner.insert(0, ET.Element(m(name + "Pr")))
    for properties in element.iter(m("naryPr")):
        # The default n-ary operator is an integral (ECMA-376 22.1.2.20).
        if properties.find(m("chr")) is None:
            ET.SubElement(properties, m("chr"), {m("val"): "∫"})
    return oMath2Latex(element).latex.strip()


def _in_fallback(node):
    return any(parent.tag == f"{{{MC}}}Fallback" for parent in node.iterancestors())


def _replace_with_token(node, token):
    parent = node.getparent()
    replacement = _token_run(token)
    # Math nested directly in a run only needs the text node.
    replacement = replacement[0] if parent.tag == w("r") else replacement
    replacement.tail = node.tail
    parent.replace(node, replacement)


def _replace_equations(root, result):
    """Swap OMML for tokens; return True when some equation fell back to text."""
    fell_back = False
    for node in list(root.iter(m("oMathPara"), m("oMath"))):
        if node.getparent() is None or _in_fallback(node):
            continue
        if node.tag == m("oMath") and any(parent.tag == m("oMathPara") for parent in node.iterancestors()):
            continue
        display = node.tag == m("oMathPara")
        parts = node.findall(m("oMath")) if display else [node]
        try:
            latex = " \\\\ ".join(filter(None, (_latex(part) for part in parts)))
        except Exception:
            latex = ""
        token = "HDMMATH" + uuid4().hex.upper()
        if latex:
            result.math[token] = ("$$" + latex + "$$") if display else ("$" + latex + "$")
        else:
            fallback = _equation_text(node).replace("`", "'")
            result.math[token] = f"`{fallback}`" if fallback else "[Equation unavailable]"
            fell_back = True
        _replace_with_token(node, token)
    return fell_back


def _label_lists(root, numbering, styles, result):
    """Replace Word numbering with literal label tokens; return ordered labels per paragraph."""
    labels = {}
    for paragraph in root.iter(w("p")):
        if _in_fallback(paragraph):
            continue
        properties = paragraph.find(w("pPr"))
        num = None if properties is None else properties.find(w("numPr"))
        if num is not None and num.find(w("numId")) is not None:
            num_id, ilvl = _val(num.find(w("numId"))), _val(num.find(w("ilvl")))
        else:
            style = None if properties is None else _val(properties.find(w("pStyle")))
            num_id, ilvl = styles.numbering(style)
            if num is not None and num.find(w("ilvl")) is not None:
                ilvl = _val(num.find(w("ilvl")))
        if not num_id or num_id == "0":
            continue
        level = int(ilvl or "0")
        label = numbering.next(num_id, level)
        if label is None:
            continue
        if properties is None:
            properties = etree.Element(w("pPr"))
            paragraph.insert(0, properties)
        if num is not None:
            properties.remove(num)
        # numId 0 explicitly disables both direct and style-linked numbering.
        disabled = etree.Element(w("numPr"))
        etree.SubElement(disabled, w("ilvl")).set(w("val"), "0")
        etree.SubElement(disabled, w("numId")).set(w("val"), "0")
        style_node = properties.find(w("pStyle"))
        properties.insert(0 if style_node is None else properties.index(style_node) + 1, disabled)
        token = "HDMLIST" + uuid4().hex.upper()
        result.lists[token] = (label[0], label[1], level, num_id)
        labels[paragraph] = label[1] if label[0] == "ordered" else ""
        properties.addnext(_token_run(token))
    return labels


def _apply_bold_overrides(root):
    """Direct w:b="0" overrides a bold character style such as Strong."""
    changed = False
    for run in root.iter(w("r")):
        properties = run.find(w("rPr"))
        bold = None if properties is None else properties.find(w("b"))
        character = None if properties is None else properties.find(w("rStyle"))
        if bold is not None and character is not None and not _on(bold):
            properties.remove(character)
            changed = True
    return changed


def _mark_headings(root, labels, styles):
    changed = False
    for paragraph in root.iter(w("p")):
        if _in_fallback(paragraph) or _in(paragraph, {w("tbl"), w("txbxContent"), w("footnote"), w("endnote")}):
            continue
        level = _heading_level(paragraph, labels.get(paragraph, ""), styles)
        if level is None:
            continue
        properties = paragraph.find(w("pPr"))
        if properties is None:
            properties = etree.Element(w("pPr"))
            paragraph.insert(0, properties)
        style = properties.find(w("pStyle"))
        if style is None:
            style = etree.Element(w("pStyle"))
            properties.insert(0, style)
        style.set(w("val"), f"HDMHeading{level}")
        _strip_bold(paragraph, styles)
        changed = True
    return changed


def _fill_alt_text(root, styles):
    changed = False
    for description in root.iter(f"{{{WP}}}docPr"):
        if _meaningful_alt(description.get("descr")):
            continue
        paragraph = next((parent for parent in description.iterancestors() if parent.tag == w("p")), None)
        caption = None if paragraph is None else _nearby_caption(paragraph, styles)
        if caption:
            description.set("descr", caption)
        elif "descr" in description.attrib:
            del description.attrib["descr"]
        else:
            continue
        changed = True
    return changed


def analyze_docx(data):
    """Return a rewritten DOCX package when Word structure needs to be exposed."""
    with ZipFile(BytesIO(data)) as archive:
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            return DocxStructure()
        root = _parse(archive.read("word/document.xml"))
        numbering = _Numbering(_parse(archive.read("word/numbering.xml")) if "word/numbering.xml" in names else None)
        styles = _Styles(_parse(archive.read("word/styles.xml")) if "word/styles.xml" in names else None)
        result = DocxStructure()

        fell_back = _replace_equations(root, result)
        labels = _label_lists(root, numbering, styles, result)
        changed = _apply_bold_overrides(root)
        changed = _mark_headings(root, labels, styles) or changed
        changed = _fill_alt_text(root, styles) or changed

        if not result.lists and not result.math and not changed:
            return DocxStructure()
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as target:
            for info in archive.infolist():
                payload = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True) \
                    if info.filename == "word/document.xml" else archive.read(info.filename)
                target.writestr(info, payload)
        result.package = output.getvalue()
        if fell_back:
            result.warnings = ("Some Word equations could not be converted to LaTeX; their plain text was kept.",)
        return result


def _marker(kind, label):
    if kind == "bullet":
        return "-"
    if kind == "ordered" and NATIVE_ORDERED.fullmatch(label):
        return label
    return "- " + label if label else "-"


def restore_structure(markdown, structure):
    """Replace list and equation tokens with Markdown that keeps the source labels."""
    for token, value in structure.math.items():
        markdown = markdown.replace(token, value)
    if not structure.lists:
        return markdown
    lines = markdown.split("\n")
    start = re.compile(r"^(HDMLIST[0-9A-F]{32})(.*)$")
    output = []
    index = 0
    while index < len(lines):
        match = start.match(lines[index])
        if not match or match.group(1) not in structure.lists:
            output.append(lines[index])
            index += 1
            continue
        # Collect consecutive numbered paragraphs, separated only by blank lines.
        group = []
        while index < len(lines):
            match = start.match(lines[index])
            if not match or match.group(1) not in structure.lists:
                break
            block = [match.group(2).lstrip()]
            index += 1
            while index < len(lines) and lines[index].strip() and not start.match(lines[index]):
                block.append(lines[index])
                index += 1
            group.append((structure.lists[match.group(1)], block))
            lookahead = index
            while lookahead < len(lines) and not lines[lookahead].strip():
                lookahead += 1
            if lookahead < len(lines) and start.match(lines[lookahead]):
                index = lookahead
            else:
                break
        stack = []
        previous_plain = True
        top_marker = None
        rendered = []
        for (kind, label, level, num_id), block in group:
            native = kind == "ordered" and NATIVE_ORDERED.fullmatch(label)
            custom = kind != "bullet" and not native
            # A custom label never nests under another list's items.
            while stack and (stack[-1][0] >= level or (custom and stack[-1][2] != num_id)):
                stack.pop()
            if not stack and custom:
                # A top-level custom label (a., 2.1., [1]) reads best as a labelled paragraph.
                text = (label + " " if label else "") + block[0]
                body = [text.rstrip()] + block[1:]
                rendered.append(("\n\n" if rendered else "") + "\n".join(body))
                previous_plain = True
                continue
            indent = stack[-1][1] if stack else 0
            marker = _marker(kind, label)
            if not stack:
                # A different top-level marker type starts a separate Markdown list.
                previous_plain = previous_plain or top_marker != marker.startswith("-")
                top_marker = marker.startswith("-")
            # Nested blocks align with the list item's content column.
            width = 2 if marker.startswith("-") else len(marker) + 1
            body = [" " * indent + marker + " " + block[0]] + [" " * (indent + width) + line.lstrip() for line in block[1:]]
            rendered.append(("\n\n" if rendered and previous_plain else "\n" if rendered else "") + "\n".join(body))
            previous_plain = False
            stack.append((level, indent + width, num_id))
        output.append("".join(rendered))
    markdown = "\n".join(output)
    # Tokens inside tables or HTML blocks keep their label inline.
    for token, (kind, label, *_) in structure.lists.items():
        markdown = markdown.replace(token, ("• " if kind == "bullet" else (label + " " if label else "")))
    return markdown
