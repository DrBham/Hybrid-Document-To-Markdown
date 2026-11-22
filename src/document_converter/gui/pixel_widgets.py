"""Pixel-styled widgets that Qt style sheets cannot express on their own."""

from __future__ import annotations

import re

from PySide6.QtCore import QPointF, QRect, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
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

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        body = self.rect().adjusted(0, 0, -self.SHADOW, -self.SHADOW)
        painter.fillRect(body.translated(self.SHADOW, self.SHADOW), QColor(COLORS["shadow"]))
        painter.fillRect(body, QColor(COLORS["border"]))
        inset = self.BORDER
        painter.fillRect(body.adjusted(inset, inset, -inset, -inset), QColor(COLORS["surface"]))
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
        # Bottom-right keeps the primary Convert/Save actions uncovered.
        self.move(parent.width() - width - 32, parent.height() - self.height() - 40)


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
