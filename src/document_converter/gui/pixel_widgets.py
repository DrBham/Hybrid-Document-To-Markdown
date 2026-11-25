"""Pixel-styled widgets that Qt style sheets cannot express on their own."""

from __future__ import annotations

import re

from PySide6.QtCore import QPointF, QRect, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QTreeWidgetItem,
    QWidget,
)

from .theme import COLORS


# 16x16 pixel icons as (x, y, w, h) fills and cut-outs, one family for every button.
PIXEL_ICONS = {
    "folder": ([(1, 3, 5, 11), (6, 4, 1, 10), (7, 5, 8, 9)], []),
    "trash": ([(5, 1, 6, 2), (1, 3, 14, 2), (2, 6, 12, 9)], [(4, 8, 2, 5), (7, 8, 2, 5), (10, 8, 2, 5)]),
    "clear": ([(2, 2, 2, 2), (4, 4, 2, 2), (6, 6, 4, 4), (10, 4, 2, 2), (12, 2, 2, 2),
               (4, 10, 2, 2), (2, 12, 2, 2), (10, 10, 2, 2), (12, 12, 2, 2)], []),
    "convert": ([(1, 7, 9, 2), (8, 4, 2, 8), (10, 5, 2, 6), (12, 6, 2, 4), (14, 7, 1, 2)], []),
    "save": ([(1, 1, 12, 14), (13, 2, 1, 13), (14, 3, 1, 12)], [(4, 2, 7, 4), (4, 9, 8, 5)]),
    "copy": ([(2, 1, 9, 2), (2, 3, 2, 9), (5, 5, 9, 10)], [(7, 7, 5, 6)]),
}


def pixel_icon(name: str, color: str) -> QIcon:
    """Draw a crisp 16 px pixel icon at 2x so it stays sharp on HiDPI screens."""
    fills, holes = PIXEL_ICONS[name]
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.scale(2, 2)
    for x, y, w, h in fills:
        painter.fillRect(x, y, w, h, QColor(color))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    for x, y, w, h in holes:
        painter.fillRect(x, y, w, h, Qt.GlobalColor.transparent)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


class PixelBackground(QWidget):
    """Window background with a subtle 8 px checker dither."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        tile = QPixmap(8, 8)
        tile.fill(QColor(COLORS["background"]))
        painter = QPainter(tile)
        painter.fillRect(0, 0, 4, 4, QColor(COLORS["dither"]))
        painter.fillRect(4, 4, 4, 4, QColor(COLORS["dither"]))
        painter.end()
        self._brush = QBrush(tile)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.fillRect(event.rect(), self._brush)
        painter.end()


def add_press_shadow(button: QAbstractButton, offset: int = 4) -> None:
    """Give a button a hard pixel shadow that collapses while it is pressed."""
    shadow = QGraphicsDropShadowEffect(button)
    shadow.setBlurRadius(0)
    shadow.setColor(QColor(COLORS["shadow"]))
    shadow.setOffset(offset, offset)
    button.setGraphicsEffect(shadow)
    button.pressed.connect(lambda: shadow.setOffset(QPointF(1, 1)))
    button.released.connect(lambda: shadow.setOffset(QPointF(offset, offset)))


class PixelCard(QFrame):
    """Square card with a hard offset shadow and corner rivets."""

    SHADOW = 6
    BORDER = 3
    RIVET = 6

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("pixelCard")
        # Reserve the shadow strip so child layouts never paint over it.
        self.setContentsMargins(0, 0, self.SHADOW, self.SHADOW)

    def border_color(self) -> str:
        return COLORS["border"]

    def surface_color(self) -> str:
        return COLORS["surface"]

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        body = self.rect().adjusted(0, 0, -self.SHADOW, -self.SHADOW)
        painter.fillRect(body.translated(self.SHADOW, self.SHADOW), QColor(COLORS["shadow"]))
        painter.fillRect(body, QColor(self.border_color()))
        inset = self.BORDER
        painter.fillRect(body.adjusted(inset, inset, -inset, -inset), QColor(self.surface_color()))
        accent = QColor(COLORS["primary"])
        painter.fillRect(QRect(body.left(), body.top(), self.RIVET, self.RIVET), accent)
        painter.fillRect(QRect(body.right() - self.RIVET + 1, body.top(), self.RIVET, self.RIVET), accent)
        painter.end()


class WorkflowSteps(QWidget):
    """Add → Convert → Save progress chips shown in the header."""

    LABELS = ("Add", "Convert", "Save")

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAccessibleName("Workflow progress")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.chips: list[QLabel] = []
        for index, label in enumerate(self.LABELS):
            chip = QLabel(f"{index + 1}  {label}")
            chip.setObjectName("stepChip")
            self.chips.append(chip)
            layout.addWidget(chip)
            if index < len(self.LABELS) - 1:
                connector = QLabel("▪▪▪")
                connector.setObjectName("stepConnector")
                connector.setAccessibleName("")
                layout.addWidget(connector)
        self.set_stage(0, ("Drop or choose documents", "Add files first", "Convert first, then save"))

    def set_stage(self, stage: int, tips: tuple[str, str, str]) -> None:
        """Mark steps before ``stage`` done, ``stage`` active, and later ones pending."""
        for index, (chip, tip) in enumerate(zip(self.chips, tips)):
            state = "done" if index < stage else "active" if index == stage else "next"
            if chip.property("state") != state:
                chip.setProperty("state", state)
                chip.style().unpolish(chip)
                chip.style().polish(chip)
            chip.setToolTip(tip)
            chip.setAccessibleName(f"Step {index + 1}, {self.LABELS[index]}: {state}. {tip}")
        self.stage = stage


class Toast(QLabel):
    """Short confirmation that pops up at the bottom of the window."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAccessibleName("Notification")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, message: str, timeout_ms: int = 2600) -> None:
        self.setText(f"■  {message}")
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self._timer.start(timeout_ms)

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        width = min(self.sizeHint().width(), parent.width() - 48)
        self.resize(width, self.sizeHint().height())
        # Inside the preview's lower-right corner: clear of Convert/Save, the card
        # border and the preview summary line.
        self.move(parent.width() - width - 56, parent.height() - self.height() - 84)


STATUS_COLORS = {
    "Pending": COLORS["muted_foreground"],
    "Converting": COLORS["primary"],
    "Converted": COLORS["success_text"],
    "Converted with warnings": COLORS["warning_chip"],
    "Saved": COLORS["success"],
    "Failed": COLORS["danger"],
    "Save failed": COLORS["danger"],
}
FINAL_STATUSES = {"Saved", "Failed", "Save failed", "Converted with warnings"}


def set_status(item: QTreeWidgetItem, status: str, column: int = 3) -> None:
    """Colour a file status in the list; final states are also bold."""
    item.setText(column, status)
    item.setForeground(column, QBrush(QColor(STATUS_COLORS.get(status, COLORS["foreground"]))))
    font = item.font(column)
    font.setBold(status in FINAL_STATUSES)
    item.setFont(column, font)


class MarkdownHighlighter(QSyntaxHighlighter):
    """Light Markdown colouring for the read-only preview."""

    # Embedded data URIs can be tens of kilobytes; skip colouring them.
    MAX_LINE = 4000

    def __init__(self, document):
        super().__init__(document)

        def style(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            fmt.setFontItalic(italic)
            return fmt

        self.heading = style(COLORS["primary"], bold=True)
        self.rules = [
            (re.compile(r"^\|.*\|\s*$"), style(COLORS["table_text"])),
            (re.compile(r"\*\*[^*\n]+\*\*"), style(COLORS["strong_text"], bold=True)),
            (re.compile(r"(?<![*\w])\*[^*\n]+\*(?!\*)"), style(COLORS["muted_foreground"], italic=True)),
            (re.compile(r"\$\$?[^$\n]+\$\$?"), style(COLORS["math_text"])),
            (re.compile(r"!\[[^\]\n]*\]\[[^\]\n]*\]|!\[[^\]\n]*\]\([^)\n]*\)"), style(COLORS["success_text"])),
            (re.compile(r"`[^`\n]+`"), style(COLORS["math_text"])),
        ]
        self.dim = style(COLORS["dim_text"])
        self.list_item = style(COLORS["success_text"])
        self.label = style(COLORS["primary_hover"], bold=True)

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt override
        if len(text) > self.MAX_LINE or text.startswith("[hybrid-media-"):
            self.setFormat(0, len(text), self.dim)
            return
        if re.match(r"^#{1,6}\s", text):
            self.setFormat(0, len(text), self.heading)
            return
        if re.match(r"^\s*(?:\|\s*:?-{3,}:?\s*)+\|\s*$|^-{3,}\s*$|^<!--", text):
            self.setFormat(0, len(text), self.dim)
            return
        marker = re.match(r"^(\s*(?:[-*+]|\d+[.)]|[a-z][.)]|\[\d+\]|\d+(?:\.\d+)+\.?))\s", text)
        if marker:
            # The whole item reads as one unit; its label stands out.
            self.setFormat(0, len(text), self.list_item)
            self.setFormat(0, len(marker.group(1)), self.label)
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)
