"""Pixel theme tokens, font loading, and Qt stylesheet."""

from pathlib import Path

from PySide6.QtGui import QFontDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_LOGO_PATH = PROJECT_ROOT / "assets" / "branding" / "app-logo.png"


COLORS = {
    "primary": "#B59A68",
    "primary_hover": "#C5AC7B",
    "primary_pressed": "#9C8457",
    "primary_light": "#D4BF91",
    "primary_dark": "#5E4F33",
    "accent": "#879285",
    "accent_hover": "#9AA497",
    "accent_pressed": "#747E72",
    "accent_light": "#B5BDB1",
    "accent_dark": "#4A5248",
    "background": "#171614",
    "dither": "#1F1D1A",
    "surface": "#211F1C",
    "surface_alt": "#2C2924",
    "surface_hover": "#39342C",
    "input": "#141311",
    "foreground": "#D8D2C5",
    "muted_foreground": "#AAA294",
    "dim_text": "#7A7368",
    "strong_text": "#F0EADC",
    "table_text": "#C8C1B3",
    "math_text": "#D7B98A",
    "border": "#4D4840",
    "border_hover": "#6B624F",
    "bevel_light": "#5A5348",
    "outline": "#0E0D0B",
    "shadow": "#0A0908",
    "danger": "#B07F6E",
    "success": "#87967D",
    "success_text": "#B9C2B5",
    "warning": "#B59A68",
    "warning_chip": "#C9A54E",
    "ink": "#171512",
    "selection": "#413D36",
    "row_hover": "#342F27",
    "scroll": "#665F54",
    "scroll_hover": "#7A7163",
    "scroll_track": "#1C1A17",
}


def load_theme_fonts() -> None:
    """Load the bundled OFL pixel font once for consistent headings."""
    font_path = PROJECT_ROOT / "assets" / "fonts" / "PressStart2P-Regular.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))


C = COLORS

# Qt has no box-shadow, so pixel depth comes from two-tone 3 px bevels: light
# top/left and dark bottom/right. Pressing swaps them and nudges the label.
APP_STYLESHEET = f"""
QMainWindow {{
    background-color: {C["background"]};
}}

QWidget {{
    color: {C["foreground"]};
    font-family: "Consolas";
    font-size: 14px;
}}

QLabel#appTitle {{
    color: {C["primary"]};
    font-family: "Press Start 2P";
    font-size: 18px;
}}

QLabel#sectionTitle {{
    color: {C["primary"]};
    font-family: "Press Start 2P";
    font-size: 12px;
}}

QLabel#mutedText, QLabel#previewFile, QLabel#summaryLabel {{
    color: {C["muted_foreground"]};
}}

QLabel#appLogo {{
    background-color: {C["surface"]};
    border: 3px solid {C["outline"]};
    padding: 3px;
}}

QLabel#stepChip {{
    font-family: "Press Start 2P";
    font-size: 8px;
    padding: 8px 10px;
    border: 3px solid {C["outline"]};
    background-color: {C["surface"]};
    color: {C["muted_foreground"]};
}}

QLabel#stepChip[state="done"] {{
    background-color: {C["surface_alt"]};
    color: {C["success_text"]};
    border-bottom-color: {C["accent"]};
}}

QLabel#stepChip[state="active"] {{
    background-color: {C["primary"]};
    color: {C["ink"]};
    border-color: {C["primary_light"]} {C["outline"]} {C["outline"]} {C["primary_light"]};
}}

QLabel#stepConnector {{
    color: {C["border"]};
    font-size: 10px;
}}

QLabel#errorBanner {{
    background-color: #302522;
    border: 3px solid {C["danger"]};
    color: #E8CFC8;
    padding: 12px 14px;
}}

QLabel#toast {{
    background-color: {C["surface"]};
    border: 3px solid {C["accent"]};
    border-bottom-width: 6px;
    border-right-width: 6px;
    border-bottom-color: {C["shadow"]};
    border-right-color: {C["shadow"]};
    color: {C["foreground"]};
    font-size: 15px;
    padding: 10px 16px;
}}

QFrame#dropZone {{
    background-color: {C["scroll_track"]};
    border: 3px dashed {C["border_hover"]};
}}

QFrame#dropZone:hover {{
    background-color: #29261F;
    border: 3px dashed {C["primary"]};
}}

QFrame#dropZone:focus {{
    border: 3px solid {C["primary"]};
}}

QFrame#dropZone[dragActive="true"] {{
    background-color: #302D24;
    border: 3px solid {C["primary"]};
}}

QLabel#fieldLabel {{
    color: {C["muted_foreground"]};
    font-weight: 600;
}}

QLabel#dropHint {{
    color: {C["muted_foreground"]};
    font-size: 12px;
}}

QLabel#mediaHelper {{
    color: {C["muted_foreground"]};
    font-size: 12px;
    padding-bottom: 2px;
}}

QPushButton {{
    background-color: {C["surface_alt"]};
    border-style: solid;
    border-width: 3px;
    border-color: {C["bevel_light"]} {C["outline"]} {C["outline"]} {C["bevel_light"]};
    border-radius: 0;
    color: {C["foreground"]};
    font-family: "Press Start 2P";
    font-size: 9px;
    min-height: 40px;
    padding: 0 16px;
}}

QPushButton:hover {{
    background-color: {C["surface_hover"]};
    color: {C["strong_text"]};
}}

QPushButton:pressed {{
    background-color: {C["selection"]};
    border-color: {C["outline"]} {C["bevel_light"]} {C["bevel_light"]} {C["outline"]};
    padding: 3px 13px 0 19px;
}}

QPushButton:focus {{
    outline: none;
    border-color: {C["primary"]};
}}

QPushButton:disabled {{
    background-color: #25231F;
    border-color: #39352F;
    color: #777166;
}}

QPushButton#primaryButton {{
    background-color: {C["primary"]};
    border-color: {C["primary_light"]} {C["primary_dark"]} {C["primary_dark"]} {C["primary_light"]};
    color: {C["ink"]};
}}

QPushButton#primaryButton:hover {{
    background-color: {C["primary_hover"]};
}}

QPushButton#primaryButton:pressed {{
    background-color: {C["primary_pressed"]};
    border-color: {C["primary_dark"]} {C["primary_light"]} {C["primary_light"]} {C["primary_dark"]};
}}

QPushButton#accentButton {{
    background-color: {C["accent"]};
    border-color: {C["accent_light"]} {C["accent_dark"]} {C["accent_dark"]} {C["accent_light"]};
    color: {C["ink"]};
}}

QPushButton#accentButton:hover {{
    background-color: {C["accent_hover"]};
}}

QPushButton#accentButton:pressed {{
    background-color: {C["accent_pressed"]};
    border-color: {C["accent_dark"]} {C["accent_light"]} {C["accent_light"]} {C["accent_dark"]};
}}

QPushButton#primaryButton:disabled, QPushButton#accentButton:disabled {{
    background-color: #25231F;
    border-color: #39352F;
    color: #777166;
}}

QPushButton#warningChip {{
    background-color: {C["warning_chip"]};
    border-color: #E2C77C #6E5A26 #6E5A26 #E2C77C;
    color: {C["ink"]};
    font-size: 8px;
    min-height: 30px;
    padding: 0 10px;
}}

QPushButton#warningChip:hover {{
    background-color: #D6B562;
}}

QPushButton#copiedButton {{
    background-color: {C["accent"]};
    border-color: {C["accent_light"]} {C["accent_dark"]} {C["accent_dark"]} {C["accent_light"]};
    color: {C["ink"]};
}}

QLineEdit, QPlainTextEdit, QTreeWidget, QComboBox {{
    background-color: {C["input"]};
    border: 3px solid {C["border"]};
    border-radius: 0;
    color: {C["foreground"]};
    selection-background-color: {C["primary"]};
    selection-color: {C["ink"]};
}}

QLineEdit {{
    min-height: 36px;
    padding: 0 10px;
}}

QComboBox {{
    min-height: 36px;
    padding: 0 10px;
}}

QLineEdit:hover, QComboBox:hover, QTreeWidget:hover, QPlainTextEdit:hover {{
    border-color: {C["border_hover"]};
}}

QComboBox::drop-down {{
    border: 0;
    width: 28px;
}}

QComboBox QAbstractItemView {{
    background-color: {C["surface_alt"]};
    border: 3px solid {C["outline"]};
    color: {C["foreground"]};
    selection-background-color: {C["selection"]};
    selection-color: {C["foreground"]};
    outline: 0;
}}

QLineEdit:focus, QPlainTextEdit:focus, QTreeWidget:focus, QComboBox:focus {{
    border-color: {C["primary"]};
}}

QPlainTextEdit {{
    font-family: "Consolas";
    font-size: 14px;
    padding: 10px;
}}

QTreeWidget {{
    alternate-background-color: #1C1A17;
    outline: 0;
}}

QTreeWidget::item {{
    min-height: 34px;
    padding: 2px 8px;
}}

QTreeWidget::item:hover {{
    background-color: {C["row_hover"]};
}}

QTreeWidget::item:selected {{
    background-color: {C["selection"]};
    color: {C["strong_text"]};
}}

QHeaderView::section {{
    background-color: {C["surface_alt"]};
    border: 0;
    border-right: 3px solid {C["input"]};
    border-bottom: 3px solid {C["border"]};
    color: {C["primary"]};
    font-family: "Press Start 2P";
    font-size: 8px;
    padding: 10px;
}}

QScrollBar:vertical {{
    background: {C["scroll_track"]};
    border: 0;
    width: 14px;
    margin: 0;
}}

QScrollBar:horizontal {{
    background: {C["scroll_track"]};
    border: 0;
    height: 14px;
    margin: 0;
}}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {C["scroll"]};
    border: 3px solid {C["scroll_track"]};
    border-radius: 0;
    min-height: 36px;
    min-width: 36px;
}}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: {C["scroll_hover"]};
}}

QScrollBar::handle:vertical:pressed, QScrollBar::handle:horizontal:pressed {{
    background: {C["primary"]};
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

QAbstractScrollArea::corner {{
    background: {C["scroll_track"]};
}}

QProgressBar {{
    background-color: {C["input"]};
    border: 3px solid {C["outline"]};
    border-radius: 0;
    max-height: 20px;
    min-height: 20px;
    padding: 2px;
}}

QProgressBar::chunk {{
    background-color: {C["primary"]};
    width: 10px;
    margin-right: 3px;
}}

QSplitter::handle {{
    background-color: transparent;
    width: 8px;
}}

QSplitter::handle:hover {{
    background-color: {C["border"]};
}}

QStatusBar {{
    background-color: {C["input"]};
    border-top: 3px solid {C["border"]};
    color: {C["muted_foreground"]};
}}

QToolTip {{
    background-color: {C["foreground"]};
    border: 3px solid {C["outline"]};
    color: {C["ink"]};
    font-family: "Consolas";
    font-size: 13px;
    padding: 5px 8px;
}}
"""
