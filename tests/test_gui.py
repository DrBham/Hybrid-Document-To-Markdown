import os
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPlainTextEdit

from document_converter.core.models import (
    BatchConversionResult,
    ConversionResult,
    FileConversionOutcome,
)
from document_converter.gui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    widget = MainWindow()
    yield widget
    widget.close()


def create_files(tmp_path: Path, *names: str) -> list[Path]:
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_text("content", encoding="utf-8")
        paths.append(path)
    return paths


def test_window_exposes_accessible_file_workflow(window):
    assert window.minimumWidth() >= 1080
    assert window.drop_zone.accessibleName() == "Document drop zone"
    assert window.drop_zone.browse_button.text() == "Choose files"
    assert window.convert_button.text() == "Convert files"
    assert window.export_button.text() == "Save Markdown"
    assert window.export_button.isHidden()
    assert not window.windowIcon().isNull()
    assert window.logo_label.pixmap() is not None
    assert not window.logo_label.pixmap().isNull()
    assert window.drop_zone.format_selector.currentText() == (
        "Text document (.txt)"
    )
    assert ".TXT" in window.drop_zone.drop_hint.text()


def test_document_panels_show_scrollbars_only_when_needed(window):
    as_needed = Qt.ScrollBarPolicy.ScrollBarAsNeeded

    assert window.file_tree.horizontalScrollBarPolicy() == as_needed
    assert window.file_tree.verticalScrollBarPolicy() == as_needed
    assert window.preview.horizontalScrollBarPolicy() == as_needed
    assert window.preview.verticalScrollBarPolicy() == as_needed
    assert window.preview.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap


def test_embedded_media_is_automatic_and_model_free(window):
    assert window.privacy_badge.text() == "Local-first processing"
    helper = window.media_helper.text().lower()
    assert "base64" in helper
    assert "automatically" in helper
    assert "no ai model" in helper


def test_file_type_selector_filters_added_files(window, tmp_path):
    pdf_index = window.drop_zone.format_selector.findText(
        "PDF document (.pdf)"
    )
    window.drop_zone.format_selector.setCurrentIndex(pdf_index)
    txt_file = create_files(tmp_path, "notes.txt")[0]

    window.add_files([txt_file])

    assert window.file_tree.topLevelItemCount() == 0
    assert ".PDF" in window.error_banner.text()


def test_add_files_accepts_same_extension_case_insensitively(
    window,
    tmp_path,
):
    files = create_files(tmp_path, "one.PDF", "two.pdf")
    pdf_index = window.drop_zone.format_selector.findText(
        "PDF document (.pdf)"
    )
    window.drop_zone.format_selector.setCurrentIndex(pdf_index)

    window.add_files(files)

    assert window.file_tree.topLevelItemCount() == 2
    assert window.summary_label.text() == "2 files selected · .PDF batch"
    assert window.convert_button.isEnabled()


def test_file_type_selector_skips_other_extensions(window, tmp_path):
    files = create_files(tmp_path, "one.pdf", "two.docx")
    pdf_index = window.drop_zone.format_selector.findText(
        "PDF document (.pdf)"
    )
    window.drop_zone.format_selector.setCurrentIndex(pdf_index)

    window.add_files(files)

    assert window.file_tree.topLevelItemCount() == 1
    assert window.file_tree.topLevelItem(0).text(0) == "one.pdf"
    assert "1 unsupported or missing file(s) skipped" in (
        window.statusBar().currentMessage()
    )


def test_conversion_result_updates_status_and_preview(window, tmp_path):
    source = create_files(tmp_path, "report.txt")[0]
    window.add_files([source])
    conversion = ConversionResult(
        source_path=source.resolve(),
        source_format="txt",
        markdown="# Report\n\nConverted locally.",
    )
    batch = BatchConversionResult(
        extension=".txt",
        outcomes=(
            FileConversionOutcome(
                source_path=source.resolve(),
                result=conversion,
            ),
        ),
    )

    window._conversion_finished(batch)

    item = window.file_tree.topLevelItem(0)
    assert item.text(3) == "Converted"
    assert window.preview.toPlainText() == conversion.markdown
    assert window.preview_file.text() == "report.txt"
    assert window.preview_file.toolTip() == str(source.resolve())
    assert window.export_button.isEnabled()
    assert not window.export_button.isHidden()


def test_clear_resets_files_results_and_preview(window, tmp_path):
    source = create_files(tmp_path, "sample.csv")[0]
    window.add_files([source])

    window._clear_files()

    assert window.file_tree.topLevelItemCount() == 0
    assert window.preview.toPlainText() == ""
    assert not window.convert_button.isEnabled()
    assert not window.export_button.isEnabled()
    assert window.export_button.isHidden()
    assert window.drop_zone.format_selector.currentIndex() == 0
    assert window.drop_zone.format_selector.currentText() == (
        "Text document (.txt)"
    )


def test_conversion_worker_and_export_complete_real_txt_workflow(
    window,
    app,
    tmp_path,
):
    source = create_files(tmp_path, "notes.txt")[0]
    output_directory = tmp_path / "markdown-output"
    window.output_path.setText(str(output_directory))
    window.add_files([source])

    window._start_conversion()
    deadline = time.monotonic() + 10
    while window._thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    assert window._thread is None
    assert window.file_tree.topLevelItem(0).text(3) == "Converted"
    assert window.preview.toPlainText()

    window._export_successful()

    assert (output_directory / "notes.md").read_text(encoding="utf-8")
    assert window.file_tree.topLevelItem(0).text(3) == "Saved"


def test_export_targets_disambiguate_duplicate_source_names(window, tmp_path):
    first = tmp_path / "first" / "report.txt"
    second = tmp_path / "second" / "report.txt"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    outcomes = [
        FileConversionOutcome(
            source_path=path.resolve(),
            result=ConversionResult(
                source_path=path.resolve(),
                source_format="txt",
                markdown=path.read_text(encoding="utf-8"),
            ),
        )
        for path in (first, second)
    ]

    targets = window._build_export_targets(outcomes, tmp_path / "output")

    assert [target.name for target in targets.values()] == [
        "report.md",
        "report (2).md",
    ]
