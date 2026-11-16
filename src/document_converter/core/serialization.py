"""Small serializers which never normalize source values."""
import html
import re


def fenced(text: str, language: str = "") -> str:
    fence = "`" * max(3, 1 + max((len(m.group()) for m in re.finditer(r"`+", text)), default=0))
    return f"{fence}{language}\n{text}" + ("" if text.endswith("\n") else "\n") + f"{fence}\n"


def table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(map(len, rows))
    if not width:
        return ""
    def cell(value):
        return (html.escape(value, quote=False).replace("\\", "\\\\")
                .replace("|", "\\|").replace("`", "&#96;")
                .replace("*", "&#42;").replace("_", "&#95;")
                .replace("[", "&#91;").replace("]", "&#93;")
                .replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>"))
    lines = ["| " + " | ".join(cell(v) for v in row + [""] * (width - len(row))) + " |" for row in rows]
    lines.insert(1, "| " + " | ".join(["---"] * width) + " |")
    return "\n".join(lines) + "\n"


def metadata_section(title: str, content: str, kind: str) -> str:
    """Keep machine-readable source evidence distinct but inside Markdown."""
    if not re.fullmatch(r"[a-z0-9-]+", kind):
        raise ValueError("metadata kind must use lowercase letters, digits, or hyphens")
    safe_title = html.escape(title, quote=False)
    return (
        f'<!-- hybrid-metadata:{kind}:start -->\n'
        f"<details>\n<summary>{safe_title}</summary>\n\n"
        f"{content.rstrip()}\n\n</details>\n"
        f'<!-- hybrid-metadata:{kind}:end -->\n'
    )
