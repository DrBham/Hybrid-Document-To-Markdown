"""Pixel theme tokens, font loading, and Qt stylesheet."""

from pathlib import Path

from PySide6.QtGui import QFontDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_LOGO_PATH = PROJECT_ROOT / "assets" / "branding" / "app-logo.png"


COLORS = {
    "primary": "#B59A68",
    "primary_hover": "#C5AC7B",
    "accent": "#879285",
    "accent_hover": "#9AA497",
    "background": "#171614",
    "surface": "#211F1C",
    "surface_alt": "#2C2924",
    "input": "#141311",
    "foreground": "#D8D2C5",
    "muted_foreground": "#AAA294",
    "border": "#4D4840",
    "danger": "#A67168",
    "success": "#87967D",
    "warning": "#B59A68",
    "ink": "#171512",
    "selection": "#413D36",
    "scroll": "#665F54",
    "scroll_hover": "#7A7163",
}


def load_theme_fonts() -> None:
    """Load the bundled OFL pixel font once for consistent headings."""
    font_path = PROJECT_ROOT / "assets" / "fonts" / "PressStart2P-Regular.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))


APP_STYLESHEET = f"""
QMainWindow, QWidget#appRoot {{
    background-color: {COLORS["background"]};
}}

QWidget {{
    color: {COLORS["foreground"]};
    font-family: "Consolas";
    font-size: 14px;
}}

QLabel#appTitle {{
    color: {COLORS["primary"]};
    font-family: "Press Start 2P";
    font-size: 18px;
    font-weight: 700;
}}

QLabel#sectionTitle {{
    color: {COLORS["primary"]};
    font-family: "Press Start 2P";
    font-size: 11px;
    font-weight: 700;
}}

QLabel#mutedText, QLabel#previewFile, QLabel#summaryLabel {{
    color: {COLORS["muted_foreground"]};
}}

QLabel#privacyBadge {{
    background-color: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["border"]};
    color: {COLORS["primary"]};
    font-family: "Press Start 2P";
    font-size: 8px;
    font-weight: 600;
    padding: 8px 12px;
}}

QLabel#errorBanner {{
    background-color: #302522;
    border: 1px solid {COLORS["danger"]};
    color: #E2C9C3;
    padding: 12px 14px;
}}

QFrame#card {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
}}

QFrame#dropZone {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
}}

QFrame#dropZone:hover {{
    background-color: #29261F;
    border-color: {COLORS["primary"]};
}}

QFrame#dropZone[dragActive="true"] {{
    background-color: #302D24;
    border: 2px solid {COLORS["primary"]};
}}

QLabel#fieldLabel {{
    color: {COLORS["muted_foreground"]};
    font-weight: 600;
}}

QLabel#dropHint {{
    color: {COLORS["muted_foreground"]};
    font-size: 12px;
}}

QLabel#mediaHelper {{
    color: {COLORS["muted_foreground"]};
    font-size: 12px;
    padding-bottom: 2px;
}}

QPushButton {{
    background-color: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    color: {COLORS["foreground"]};
    font-family: "Press Start 2P";
    font-size: 9px;
    font-weight: 600;
    min-height: 44px;
    padding: 0 16px;
}}

QPushButton:hover {{
    background-color: #39342C;
    border-color: {COLORS["primary_hover"]};
    color: {COLORS["foreground"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["selection"]};
    border-color: {COLORS["primary"]};
    color: {COLORS["foreground"]};
}}

QPushButton:focus {{
    border: 2px solid {COLORS["primary"]};
}}

QPushButton:disabled {{
    background-color: #25231F;
    border-color: #39352F;
    color: #777166;
}}

QPushButton#primaryButton {{
    background-color: {COLORS["primary"]};
    border-color: {COLORS["primary"]};
    color: {COLORS["ink"]};
}}

QPushButton#primaryButton:hover {{
    background-color: {COLORS["primary_hover"]};
    border-color: #D4BF91;
}}

QPushButton#accentButton {{
    background-color: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
    color: {COLORS["ink"]};
}}

QPushButton#accentButton:hover {{
    background-color: {COLORS["accent_hover"]};
    border-color: #B5BDB1;
}}

QLineEdit, QPlainTextEdit, QTreeWidget, QComboBox {{
    background-color: {COLORS["input"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 5px;
    color: {COLORS["foreground"]};
    selection-background-color: {COLORS["primary"]};
    selection-color: {COLORS["ink"]};
}}

QLineEdit {{
    min-height: 42px;
    padding: 0 12px;
}}

QComboBox {{
    min-height: 42px;
    padding: 0 12px;
}}

QComboBox:hover {{
    border-color: {COLORS["primary"]};
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["border"]};
    color: {COLORS["foreground"]};
    selection-background-color: {COLORS["selection"]};
    selection-color: {COLORS["foreground"]};
    outline: 0;
}}

QLineEdit:focus, QPlainTextEdit:focus, QTreeWidget:focus, QComboBox:focus {{
    border: 2px solid {COLORS["primary"]};
}}

QPlainTextEdit {{
    font-family: "Consolas";
    font-size: 13px;
    padding: 12px;
}}

QTreeWidget {{
    alternate-background-color: #1C1A17;
    outline: 0;
}}

QTreeWidget::item {{
    min-height: 38px;
    padding: 3px 8px;
}}

QTreeWidget::item:hover {{
    background-color: #342F27;
    color: {COLORS["foreground"]};
}}

QTreeWidget::item:selected {{
    background-color: {COLORS["selection"]};
    color: {COLORS["foreground"]};
}}

QHeaderView::section {{
    background-color: {COLORS["surface_alt"]};
    border: 0;
    border-right: 1px solid {COLORS["border"]};
    border-bottom: 1px solid {COLORS["border"]};
    color: {COLORS["primary"]};
    font-family: "Press Start 2P";
    font-size: 8px;
    font-weight: 700;
    padding: 10px;
}}

QScrollBar:vertical {{
    background: transparent;
    border: 0;
    width: 12px;
    margin: 2px;
}}

QScrollBar:horizontal {{
    background: transparent;
    border: 0;
    height: 12px;
    margin: 2px;
}}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {COLORS["scroll"]};
    border: 0;
    border-radius: 5px;
    min-height: 36px;
    min-width: 36px;
}}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: {COLORS["scroll_hover"]};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    background: transparent;
    border: 0;
    height: 0;
    width: 0;
}}

QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

QProgressBar {{
    background-color: {COLORS["input"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    max-height: 10px;
    min-height: 10px;
}}

QProgressBar::chunk {{
    background-color: {COLORS["primary"]};
    border-radius: 3px;
}}

QSplitter::handle {{
    background-color: {COLORS["border"]};
    width: 3px;
}}

QStatusBar {{
    background-color: {COLORS["input"]};
    border-top: 1px solid {COLORS["border"]};
    color: {COLORS["muted_foreground"]};
}}

QToolTip {{
    background-color: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["primary"]};
    color: {COLORS["foreground"]};
    font-family: "Consolas";
    padding: 6px;
}}
"""
