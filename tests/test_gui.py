import os
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QMimeData, QPoint, QPointF, QUrl, Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
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


def file_mime(*paths: Path) -> QMimeData:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    return mime


def drop_event(mime: QMimeData) -> QDropEvent:
    event = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    # QDropEvent keeps a native pointer, not a Python ownership reference.
    event._test_mime = mime
    return event


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
    assert "automatically" in window.drop_zone.format_selector.toolTip()


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


def test_gui_uses_compact_user_facing_pdf_profile(window):
    options = window._batch_converter._process.options

    assert options.pdf_mode == "images"
    assert options.metadata_mode == "omit"


def test_file_type_selector_filters_added_files(window, tmp_path):
    pdf_index = window.drop_zone.format_selector.findText(
        "PDF document (.pdf)"
    )
    window.drop_zone.format_selector.setCurrentIndex(pdf_index)
    txt_file = create_files(tmp_path, "notes.txt")[0]

    window.add_files([txt_file])

    assert window.file_tree.topLevelItemCount() == 0
    assert ".PDF" in window.error_banner.text()


@pytest.mark.parametrize(
    "extension",
    ["txt", "docx", "pdf", "pptx", "xlsx", "csv", "html", "htm", "json", "xml"],
)
def test_drop_auto_detects_every_supported_extension(window, tmp_path, extension):
    source = create_files(tmp_path, f"Laporan café 01.{extension.upper()}")[0]
    event = drop_event(file_mime(source))

    window.drop_zone.dropEvent(event)

    assert event.isAccepted()
    assert window.file_tree.topLevelItemCount() == 1
    assert window.file_tree.topLevelItem(0).text(0) == source.name
    assert window.drop_zone.selected_extensions() == (f".{extension}",)


@pytest.mark.filterwarnings("ignore:Function.*QDrag.*deprecated:DeprecationWarning")
def test_drag_events_accept_supported_local_file_and_show_feedback(window, tmp_path):
    source = create_files(tmp_path, "drag me.pdf")[0]
    mime = file_mime(source)
    enter = QDragEnterEvent(
        QPoint(10, 10), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    move = QDragMoveEvent(
        QPoint(12, 12), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )

    window.drop_zone.dragEnterEvent(enter)
    window.drop_zone.dragMoveEvent(move)

    assert enter.isAccepted() and move.isAccepted()
    assert window.drop_zone.property("dragActive") is True


@pytest.mark.filterwarnings("ignore:Function.*QDrag.*deprecated:DeprecationWarning")
def test_add_documents_children_forward_drop_to_drop_zone(window, tmp_path):
    source = create_files(tmp_path, "dropped over file selector.PDF")[0]
    mime = file_mime(source)
    enter = QDragEnterEvent(
        QPoint(500, 500), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    dropped = drop_event(mime)

    target = window.drop_zone.format_selector
    assert target.acceptDrops()
    QApplication.sendEvent(target, enter)
    QApplication.sendEvent(target, dropped)

    assert enter.isAccepted() and dropped.isAccepted()
    assert window.file_tree.topLevelItemCount() == 1
    assert window.file_tree.topLevelItem(0).text(0) == source.name
    assert window.drop_zone.selected_extensions() == (".pdf",)
    assert window.drop_zone.property("dragActive") is False


@pytest.mark.filterwarnings("ignore:Function.*QDrag.*deprecated:DeprecationWarning")
def test_selected_files_panel_is_not_a_drop_target(window):
    assert not window.file_tree.viewport().acceptDrops()


@pytest.mark.filterwarnings("ignore:Function.*QDrag.*deprecated:DeprecationWarning")
def test_drag_rejects_non_url_and_unsupported_payloads(window, tmp_path):
    unsupported = create_files(tmp_path, "archive.zip")[0]
    for mime in (QMimeData(), file_mime(unsupported)):
        event = QDragEnterEvent(
            QPoint(10, 10), Qt.DropAction.CopyAction, mime,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
        )
        window.drop_zone.dragEnterEvent(event)
        assert not event.isAccepted()


def test_drop_accepts_same_type_batch_and_reports_skipped_files(window, tmp_path):
    first, second, unsupported = create_files(
        tmp_path, "one file.PDF", "dua_日本語.pdf", "notes.exe"
    )

    window.drop_zone.dropEvent(drop_event(file_mime(first, second, unsupported)))

    assert window.file_tree.topLevelItemCount() == 2
    assert window.summary_label.text() == "2 files selected · .PDF batch"
    assert "1 unsupported or missing file(s) skipped" in window.statusBar().currentMessage()


def test_drop_rejects_mixed_supported_formats_without_partial_state(window, tmp_path):
    pdf, docx = create_files(tmp_path, "one.pdf", "two.docx")

    window.drop_zone.dropEvent(drop_event(file_mime(pdf, docx)))

    assert window.file_tree.topLevelItemCount() == 0
    assert "different formats" in window.error_banner.text()
    assert window.drop_zone.selected_extensions() == (".txt",)


def test_browse_still_uses_selected_format(window, tmp_path, monkeypatch):
    source = create_files(tmp_path, "chosen file.pdf")[0]
    pdf_index = window.drop_zone.format_selector.findText("PDF document (.pdf)")
    window.drop_zone.format_selector.setCurrentIndex(pdf_index)
    monkeypatch.setattr(
        "document_converter.gui.main_window.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([str(source)], "PDF document (*.pdf)"),
    )

    window._choose_files()

    assert window.file_tree.topLevelItemCount() == 1
    assert window.file_tree.topLevelItem(0).text(0) == source.name


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


def test_large_preview_copies_and_exports_complete_result(window, app, tmp_path):
    source = create_files(tmp_path, "large.txt")[0]
    window.add_files([source])
    text = "x" * 200_010 + "END"
    result = ConversionResult(source.resolve(), "txt", text, ("Example warning",))
    window._conversion_finished(BatchConversionResult(".txt", (FileConversionOutcome(source.resolve(), result=result),)))
    assert len(window.preview.toPlainText()) == 200_000
    assert "Preview shortened" in window.preview_summary.text()
    assert window.file_tree.topLevelItem(0).text(3) == "Converted with warnings"
    window._copy_preview()
    assert app.clipboard().text() == text
    window.output_path.setText(str(tmp_path))
    window._export_successful()
    assert (tmp_path / "large.md").read_text() == text


def test_gui_remains_responsive_and_cancels_active_parser(window, app, tmp_path, monkeypatch):
    import sys
    script = tmp_path / "slow_worker.py"
    ready = tmp_path / "ready"
    script.write_text("import pathlib, sys, time\npathlib.Path(sys.argv[1]).write_text('ready')\ntime.sleep(60)\n")
    monkeypatch.setattr(window._batch_converter._process, "_command",
                        lambda request: [sys.executable, str(script), str(ready)])
    window.add_files(create_files(tmp_path, "slow.txt"))
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    window._start_conversion()
    try:
        deadline = time.monotonic() + 10
        while (not ready.exists() or len(ticks) < 3) and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        assert ready.exists() and len(ticks) >= 3
        assert window.cancel_button.isEnabled()
        window.cancel_button.click()
        deadline = time.monotonic() + 5
        while window._thread is not None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        assert window._thread is None
        assert window.export_button.isHidden()
        assert window.convert_button.isEnabled()
    finally:
        timer.stop()
        window._batch_converter.cancel()
        deadline = time.monotonic() + 5
        while window._thread is not None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
