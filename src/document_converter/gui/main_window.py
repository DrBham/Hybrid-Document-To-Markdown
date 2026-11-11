"""Main PySide6 window for the document conversion workflow."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, Qt, QThread, Signal, Slot
from PySide6.QtGui import (
    QCloseEvent,
    QCursor,
    QDragEnterEvent,
    QDropEvent,
    QFontDatabase,
    QIcon,
    QKeyEvent,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.models import BatchConversionResult, FileConversionOutcome
from ..core.validator import SUPPORTED_FORMATS
from ..services.batch_converter import BatchConverter
from ..services.markdown_exporter import MarkdownExporter
from .theme import APP_LOGO_PATH, APP_STYLESHEET, load_theme_fonts


FILE_FILTER = (
    "Supported documents "
    "(*.txt *.docx *.pdf *.pptx *.xlsx *.csv *.html *.htm *.json *.xml)"
)

FORMAT_OPTIONS = (
    ("Text document (.txt)", (".txt",)),
    ("Word document (.docx)", (".docx",)),
    ("PDF document (.pdf)", (".pdf",)),
    ("PowerPoint (.pptx)", (".pptx",)),
    ("Excel workbook (.xlsx)", (".xlsx",)),
    ("CSV data (.csv)", (".csv",)),
    ("HTML document (.html)", (".html",)),
    ("HTM document (.htm)", (".htm",)),
    ("JSON data (.json)", (".json",)),
    ("XML document (.xml)", (".xml",)),
)

class DropZone(QFrame):
    """Accessible drag-and-drop surface with a file-picker alternative."""

    paths_dropped = Signal(list)
    browse_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Document drop zone")
        self.setAccessibleDescription(
            "Drop documents here or press Enter to open the file picker"
        )
        self.setMinimumHeight(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Add documents")
        title.setObjectName("sectionTitle")

        helper = QLabel(
            "Choose a file type, then browse or drag matching files into this panel."
        )
        helper.setObjectName("mutedText")
        helper.setWordWrap(True)

        selector_row = QHBoxLayout()
        selector_row.setSpacing(10)
        selector_label = QLabel("File type")
        selector_label.setObjectName("fieldLabel")

        self.format_selector = QComboBox()
        self.format_selector.setAccessibleName("Document file type")
        self.format_selector.setToolTip(
            "Limit browsing and drag-and-drop to one supported extension"
        )
        for label, extensions in FORMAT_OPTIONS:
            self.format_selector.addItem(label, extensions)

        self.browse_button = QPushButton("Choose files")
        self.browse_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        )
        self.browse_button.setAccessibleName("Choose document files")
        self.browse_button.setToolTip("Open the file picker")
        self.browse_button.clicked.connect(self.browse_requested)

        self.drop_hint = QLabel()
        self.drop_hint.setObjectName("dropHint")
        self.drop_hint.setWordWrap(True)
        self.format_selector.currentIndexChanged.connect(
            self._update_drop_hint
        )
        self._update_drop_hint()

        layout.addWidget(title)
        layout.addWidget(helper)
        selector_row.addWidget(selector_label)
        selector_row.addWidget(self.format_selector, stretch=1)
        selector_row.addWidget(self.browse_button)
        layout.addLayout(selector_row)
        layout.addWidget(self.drop_hint)

    @Slot()
    def _update_drop_hint(self) -> None:
        extensions = " / ".join(
            extension.upper()
            for extension in self.selected_extensions()
        )
        self.drop_hint.setText(
            f"Drag and drop {extensions} files into this panel."
        )
        self.setAccessibleDescription(
            f"Accepts {extensions} files. Press Enter to open the file picker."
        )

    def selected_extensions(self) -> tuple[str, ...]:
        data = self.format_selector.currentData()
        return tuple(data) if data else ()

    def file_dialog_filter(self) -> str:
        extensions = self.selected_extensions()
        if not extensions:
            return FILE_FILTER
        patterns = " ".join(f"*{extension}" for extension in extensions)
        return f"{self.format_selector.currentText()} ({patterns})"

    def select_extension(self, extension: str) -> None:
        normalized = extension.lower()
        for index in range(self.format_selector.count()):
            data = tuple(self.format_selector.itemData(index) or ())
            if normalized in data:
                self.format_selector.setCurrentIndex(index)
                return

    def reset_format(self) -> None:
        self.format_selector.setCurrentIndex(0)

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_active(False)
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.browse_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

class ConversionWorker(QObject):
    """Run a batch conversion outside the GUI thread."""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, service: BatchConverter, paths: tuple[Path, ...]):
        super().__init__()
        self._service = service
        self._paths = paths

    @Slot()
    def run(self) -> None:
        try:
            result = self._service.convert(self._paths)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.finished.emit(result)


class MainWindow(QMainWindow):
    """Coordinate file selection, conversion, preview, and export."""

    def __init__(
        self,
        batch_converter: BatchConverter | None = None,
        exporter: MarkdownExporter | None = None,
    ):
        super().__init__()
        self._batch_converter = (
            batch_converter if batch_converter is not None else BatchConverter()
        )
        self._exporter = exporter if exporter is not None else MarkdownExporter()
        self._files: list[Path] = []
        self._items: dict[str, QTreeWidgetItem] = {}
        self._outcomes: dict[str, FileConversionOutcome] = {}
        self._thread: QThread | None = None
        self._worker: ConversionWorker | None = None

        self.setWindowTitle("Hybrid Document to Markdown")
        if APP_LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_LOGO_PATH)))
        self.setMinimumSize(1080, 720)
        self.resize(1280, 820)
        load_theme_fonts()
        self.setStyleSheet(APP_STYLESHEET)
        self._build_ui()
        self._configure_interaction_cursors()
        self._connect_signals()
        self._update_actions()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)

        page = QVBoxLayout(root)
        page.setContentsMargins(28, 24, 28, 18)
        page.setSpacing(18)
        page.addLayout(self._build_header())

        self.error_banner = QLabel()
        self.error_banner.setObjectName("errorBanner")
        self.error_banner.setWordWrap(True)
        self.error_banner.setAccessibleName("Workflow error")
        self.error_banner.hide()
        page.addWidget(self.error_banner)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_workflow_panel())
        splitter.addWidget(self._build_preview_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([690, 450])
        page.addWidget(splitter, stretch=1)

        self.statusBar().showMessage("Ready — local conversion only")

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(16)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)

        self.logo_label = QLabel()
        self.logo_label.setObjectName("appLogo")
        self.logo_label.setFixedSize(52, 52)
        self.logo_label.setAccessibleName("")
        if APP_LOGO_PATH.exists():
            logo = QPixmap(str(APP_LOGO_PATH))
            self.logo_label.setPixmap(
                logo.scaled(
                    52,
                    52,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
            )
        title = QLabel("Hybrid Document to Markdown")
        title.setObjectName("appTitle")
        subtitle = QLabel(
            "Convert local documents, review Markdown, then export when ready."
        )
        subtitle.setObjectName("mutedText")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)

        self.privacy_badge = QLabel("Local-first processing")
        self.privacy_badge.setObjectName("privacyBadge")
        self.privacy_badge.setAccessibleName(
            "Local-first processing. No cloud upload is used."
        )

        header.addWidget(self.logo_label)
        header.addLayout(title_stack)
        header.addStretch()
        header.addWidget(
            self.privacy_badge,
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        return header

    def _build_workflow_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(16)

        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)

        files_card = QFrame()
        files_card.setObjectName("card")
        files_layout = QVBoxLayout(files_card)
        files_layout.setContentsMargins(16, 14, 16, 16)
        files_layout.setSpacing(10)

        files_header = QVBoxLayout()
        files_header.setSpacing(10)
        files_title_row = QHBoxLayout()
        files_title = QLabel("Selected files")
        files_title.setObjectName("sectionTitle")
        self.summary_label = QLabel("0 files selected")
        self.summary_label.setObjectName("summaryLabel")
        files_title_row.addWidget(files_title)
        files_title_row.addWidget(self.summary_label)
        files_title_row.addStretch()

        self.remove_button = QPushButton("Remove selected")
        self.remove_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton)
        )
        self.clear_button = QPushButton("Clear all")
        self.clear_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)
        )
        files_actions = QHBoxLayout()
        files_actions.addStretch()
        files_actions.addWidget(self.remove_button)
        files_actions.addWidget(self.clear_button)

        self.remove_button.setToolTip("Remove the highlighted files")
        self.clear_button.setToolTip("Remove every file from this batch")

        files_header.addLayout(files_title_row)
        files_header.addLayout(files_actions)

        self.file_tree = QTreeWidget()
        self.file_tree.setAccessibleName("Selected document list")
        self.file_tree.setHeaderLabels(["File", "Type", "Size", "Status"])
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setMouseTracking(True)
        self.file_tree.setRootIsDecorated(False)
        self.file_tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.file_tree.setMinimumHeight(180)
        self.file_tree.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.file_tree.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.file_tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.file_tree.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        header = self.file_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setMinimumSectionSize(96)

        files_layout.addLayout(files_header)
        files_layout.addWidget(self.file_tree)
        layout.addWidget(files_card, stretch=1)

        output_card = QFrame()
        output_card.setObjectName("card")
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(16, 14, 16, 16)
        output_layout.setSpacing(10)

        output_title = QLabel("Conversion and output")
        output_title.setObjectName("sectionTitle")

        self.media_helper = QLabel(
            "Images from PDF, DOCX, PPTX, and XLSX are embedded automatically "
            "inside the Markdown file as Base64. No AI model is required."
        )
        self.media_helper.setObjectName("mediaHelper")
        self.media_helper.setAccessibleName(
            "Automatic single-file image embedding information"
        )
        self.media_helper.setWordWrap(True)
        output_row = QHBoxLayout()
        self.output_path = QLineEdit(self._default_output_directory())
        self.output_path.setReadOnly(True)
        self.output_path.setAccessibleName("Markdown output directory")
        self.choose_output_button = QPushButton("Choose folder")
        self.choose_output_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        )
        self.choose_output_button.setToolTip("Choose where Markdown files are saved")
        output_row.addWidget(self.output_path, stretch=1)
        output_row.addWidget(self.choose_output_button)

        action_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setAccessibleName("Conversion in progress")
        self.progress.hide()
        action_row.addWidget(self.progress, stretch=1)
        self.cancel_button = QPushButton("Cancel conversion")
        self.cancel_button.setToolTip("Stop the current conversion and cancel remaining files; completed results are kept")
        self.cancel_button.clicked.connect(self._batch_converter.cancel)
        self.cancel_button.hide()
        action_row.addWidget(self.cancel_button)

        self.convert_button = QPushButton("Convert files")
        self.convert_button.setObjectName("primaryButton")
        self.convert_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )
        self.convert_button.setToolTip("Convert the selected documents locally")
        self.export_button = QPushButton("Save Markdown")
        self.export_button.setObjectName("accentButton")
        self.export_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        self.export_button.setAccessibleName("Save converted Markdown files")
        self.export_button.setToolTip(
            "Save successful conversions to the selected output folder"
        )
        action_row.addWidget(self.convert_button)
        action_row.addWidget(self.export_button)

        output_layout.addWidget(output_title)
        output_layout.addWidget(self.media_helper)
        output_layout.addLayout(output_row)
        output_layout.addLayout(action_row)
        layout.addWidget(output_card)
        return panel

    def _build_preview_panel(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Markdown preview")
        title.setObjectName("sectionTitle")
        self.preview_file = QLabel("Select a converted file")
        self.preview_file.setObjectName("previewFile")
        self.preview_file.setWordWrap(True)
        self.preview_file.setMinimumWidth(0)
        self.preview_file.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        self.preview_file.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.copy_button = QPushButton("Copy")
        self.copy_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        )
        self.copy_button.setAccessibleName("Copy Markdown preview")
        self.copy_button.setToolTip("Copy the complete Markdown preview")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.copy_button, alignment=Qt.AlignmentFlag.AlignTop)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText(
            "Converted Markdown will appear here.\n\n"
            "Choose one or more documents, convert them, then select a successful "
            "row to inspect its result."
        )
        self.preview.setAccessibleName("Markdown preview")
        self.preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.preview.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.preview.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.preview.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        self.preview.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.preview_summary = QLabel("No conversion result yet")
        self.preview_summary.setObjectName("summaryLabel")

        layout.addLayout(header)
        layout.addWidget(self.preview_file)
        layout.addWidget(self.preview, stretch=1)
        layout.addWidget(self.preview_summary)
        return card

    def _connect_signals(self) -> None:
        self.drop_zone.browse_requested.connect(self._choose_files)
        self.drop_zone.paths_dropped.connect(self.add_files)
        self.remove_button.clicked.connect(self._remove_selected)
        self.clear_button.clicked.connect(self._clear_files)
        self.choose_output_button.clicked.connect(self._choose_output_directory)
        self.convert_button.clicked.connect(self._start_conversion)
        self.export_button.clicked.connect(self._export_successful)
        self.copy_button.clicked.connect(self._copy_preview)
        self.file_tree.itemSelectionChanged.connect(self._show_selected_preview)
        self.file_tree.itemEntered.connect(self._show_file_hover_hint)

    def _configure_interaction_cursors(self) -> None:
        pointer = QCursor(Qt.CursorShape.PointingHandCursor)
        for button in self.findChildren(QPushButton):
            button.setCursor(pointer)
        for combo_box in self.findChildren(QComboBox):
            combo_box.setCursor(pointer)
        self.file_tree.viewport().setCursor(pointer)

    @Slot(object, int)
    def _show_file_hover_hint(
        self,
        item: QTreeWidgetItem,
        _column: int,
    ) -> None:
        path = item.data(0, Qt.ItemDataRole.UserRole)
        status = item.text(3)
        if path:
            self.statusBar().showMessage(f"{path} — {status}", 3500)

    @staticmethod
    def _path_key(path: Path) -> str:
        return str(path.resolve()).casefold()

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KiB"
        return f"{size / (1024 * 1024):.1f} MiB"

    @staticmethod
    def _default_output_directory() -> str:
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        base = Path(documents) if documents else Path.home()
        return str(base / "Markdown Output")

    @Slot()
    def _choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose documents",
            "",
            self.drop_zone.file_dialog_filter(),
        )
        if paths:
            self.add_files(paths)

    @Slot(list)
    def add_files(self, raw_paths: Iterable[str | Path]) -> None:
        if self._thread is not None:
            self.statusBar().showMessage(
                "Wait for the current conversion before changing the batch",
                4000,
            )
            return

        candidates = [Path(path) for path in raw_paths]
        selected_extensions = set(self.drop_zone.selected_extensions())
        valid = [
            path
            for path in candidates
            if path.is_file()
            and path.suffix.lower() in SUPPORTED_FORMATS
            and (
                not selected_extensions
                or path.suffix.lower() in selected_extensions
            )
        ]
        skipped = len(candidates) - len(valid)

        if not valid:
            if selected_extensions:
                expected = ", ".join(sorted(selected_extensions)).upper()
                self._show_error(
                    f"No matching files were added. Choose an existing {expected} "
                    "file or change the file type list."
                )
            else:
                self._show_error(
                    "No supported files were added. Choose an existing TXT, DOCX, "
                    "PDF, PPTX, XLSX, CSV, HTML, JSON, or XML file."
                )
            return

        all_extensions = {
            path.suffix.lower()
            for path in [*self._files, *valid]
        }
        if len(all_extensions) > 1:
            self._show_error(
                "A batch can contain only one file type. Clear the current list "
                "or choose files with the same extension."
            )
            return

        added = 0
        for path in valid:
            resolved = path.resolve()
            key = self._path_key(resolved)
            if key in self._items:
                continue

            item = QTreeWidgetItem([
                resolved.name,
                resolved.suffix.lower().lstrip(".").upper(),
                self._format_size(resolved.stat().st_size),
                "Pending",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, str(resolved))
            item.setToolTip(0, str(resolved))
            self.file_tree.addTopLevelItem(item)
            self._files.append(resolved)
            self._items[key] = item
            added += 1

        if added:
            self.drop_zone.select_extension(self._files[0].suffix)
            self._hide_error()
            message = f"Added {added} file(s)"
            if skipped:
                message += f" · {skipped} unsupported or missing file(s) skipped"
            self.statusBar().showMessage(message, 5000)
        else:
            self.statusBar().showMessage("Those files are already selected", 4000)

        self._update_actions()

    @Slot()
    def _remove_selected(self) -> None:
        selected = list(self.file_tree.selectedItems())
        for item in selected:
            path = Path(item.data(0, Qt.ItemDataRole.UserRole))
            key = self._path_key(path)
            self._files = [file for file in self._files if self._path_key(file) != key]
            self._items.pop(key, None)
            self._outcomes.pop(key, None)
            index = self.file_tree.indexOfTopLevelItem(item)
            self.file_tree.takeTopLevelItem(index)

        self._reset_preview_if_needed()
        if not self._files:
            self.drop_zone.reset_format()
        self._update_actions()

    @Slot()
    def _clear_files(self) -> None:
        self.file_tree.clear()
        self._files.clear()
        self._items.clear()
        self._outcomes.clear()
        self.drop_zone.reset_format()
        self._hide_error()
        self.preview.clear()
        self.preview_file.setText("Select a converted file")
        self.preview_summary.setText("No conversion result yet")
        self._update_actions()

    @Slot()
    def _choose_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Choose Markdown output folder",
            self.output_path.text(),
        )
        if directory:
            self.output_path.setText(directory)

    @Slot()
    def _start_conversion(self) -> None:
        if not self._files or self._thread is not None:
            return

        self._hide_error()
        self._outcomes.clear()
        self.export_button.hide()
        for item in self._items.values():
            item.setText(3, "Converting")
            item.setToolTip(3, "")

        self._set_busy(True)
        self.statusBar().showMessage(
            "Converting files and embedding document images locally…"
        )

        self._thread = QThread(self)
        self._batch_converter.reset_cancellation()
        self._worker = ConversionWorker(
            self._batch_converter,
            tuple(self._files),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._conversion_finished)
        self._worker.failed.connect(self._conversion_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread_finished)
        self._thread.start()

    @Slot(object)
    def _conversion_finished(self, batch: BatchConversionResult) -> None:
        self._outcomes = {
            self._path_key(outcome.source_path): outcome
            for outcome in batch.outcomes
        }

        for outcome in batch.outcomes:
            item = self._items[self._path_key(outcome.source_path)]
            if outcome.succeeded:
                item.setText(3, "Converted with warnings" if outcome.result.warnings else "Converted")
                item.setToolTip(3, "\n".join(outcome.result.warnings))
            else:
                item.setText(3, "Failed")
                item.setToolTip(3, outcome.error or "Conversion failed")

        succeeded = len(batch.successful)
        failed = len(batch.failed)
        self.preview_summary.setText(
            f"{succeeded} converted · {failed} failed"
        )

        if failed:
            self._show_error(
                f"{failed} file(s) could not be converted. Select a failed row "
                "to review the error, then remove or replace that file."
            )

        first_success = next(
            (outcome for outcome in batch.outcomes if outcome.succeeded),
            None,
        )
        if first_success is not None:
            item = self._items[self._path_key(first_success.source_path)]
            self.file_tree.setCurrentItem(item)
            item.setSelected(True)
            self._display_outcome(first_success)

        self.statusBar().showMessage(
            f"Conversion complete — {succeeded} succeeded, {failed} failed",
            6000,
        )
        self._update_actions()

    @Slot(str)
    def _conversion_failed(self, message: str) -> None:
        for item in self._items.values():
            item.setText(3, "Failed")
            item.setToolTip(3, message)
        self._show_error(
            f"The batch could not start: {message}. Check the selected files and "
            "try again."
        )
        self.statusBar().showMessage("Conversion failed", 6000)

    @Slot()
    def _thread_finished(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._set_busy(False)
        self._update_actions()

    @Slot()
    def _show_selected_preview(self) -> None:
        selected = self.file_tree.selectedItems()
        if not selected:
            return
        path = Path(selected[0].data(0, Qt.ItemDataRole.UserRole))
        outcome = self._outcomes.get(self._path_key(path))
        if outcome is not None:
            self._display_outcome(outcome)
            return

        self._set_preview_filename(path)
        self.preview.clear()
        self.preview_summary.setText("Not converted yet")

    def _display_outcome(self, outcome: FileConversionOutcome) -> None:
        self._set_preview_filename(outcome.source_path)
        if outcome.succeeded and outcome.result is not None:
            preview_limit = 200_000
            self.preview.setPlainText(outcome.result.markdown[:preview_limit])
            lines = outcome.result.markdown.count("\n") + 1
            characters = len(outcome.result.markdown)
            self.preview_summary.setText(
                f"{lines} lines · {characters} characters"
                + (" · Preview shortened; Copy and Save retain full content" if characters > preview_limit else "")
                + (f" · {len(outcome.result.warnings)} warning(s)" if outcome.result.warnings else "")
            )
            self.preview_summary.setToolTip("\n".join(outcome.result.warnings))
        else:
            self.preview.setPlainText(outcome.error or "Conversion failed")
            self.preview_summary.setText("Conversion failed — review the message")

    def _set_preview_filename(self, path: Path) -> None:
        """Show a long unspaced filename without clipping the preview header."""
        name = path.name
        display_name = "\u200b".join(name) if len(name) > 48 else name
        self.preview_file.setText(display_name)
        self.preview_file.setToolTip(str(path))
        self.preview_file.setAccessibleName(f"Preview file: {name}")

    @Slot()
    def _copy_preview(self) -> None:
        text = self.preview.toPlainText()
        selected = self.file_tree.selectedItems()
        if selected:
            path = Path(selected[0].data(0, Qt.ItemDataRole.UserRole))
            outcome = self._outcomes.get(self._path_key(path))
            if outcome and outcome.result:
                text = outcome.result.markdown
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("Markdown copied to clipboard", 3000)

    @Slot()
    def _export_successful(self) -> None:
        successful = [
            outcome
            for outcome in self._outcomes.values()
            if outcome.succeeded and outcome.result is not None
        ]
        if not successful:
            return

        output_directory = Path(self.output_path.text())
        try:
            output_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._show_error(
                f"The output folder could not be created: {exc}. Choose another "
                "folder and try again."
            )
            return

        targets = self._build_export_targets(successful, output_directory)
        existing = [target for target in targets.values() if target.exists()]

        overwrite = False
        if existing:
            response = QMessageBox.question(
                self,
                "Existing Markdown files",
                f"{len(existing)} output file(s) already exist. Overwrite them?\n\n"
                "Choose No to keep existing files and export only new ones.",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.No,
            )
            if response == QMessageBox.StandardButton.Cancel:
                return
            overwrite = response == QMessageBox.StandardButton.Yes

        exported = 0
        skipped = 0
        failures: list[str] = []

        for outcome in successful:
            result = outcome.result
            if result is None:
                continue
            target = targets[self._path_key(outcome.source_path)]
            if target.exists() and not overwrite:
                skipped += 1
                continue

            try:
                self._exporter.export(
                    result.markdown,
                    target,
                    overwrite=overwrite,
                )
            except OSError as exc:
                failures.append(f"{target.name}: {exc}")
                item = self._items[self._path_key(outcome.source_path)]
                item.setText(3, "Save failed")
                item.setToolTip(3, str(exc))
            else:
                exported += 1
                item = self._items[self._path_key(outcome.source_path)]
                item.setText(3, "Saved")
                item.setToolTip(3, str(target))

        if failures:
            self._show_error(
                f"{len(failures)} file(s) could not be saved. Check folder "
                "permissions and try again."
            )
        else:
            self._hide_error()

        self.statusBar().showMessage(
            f"Save complete — {exported} saved, {skipped} skipped, "
            f"{len(failures)} failed",
            7000,
        )

    def _build_export_targets(
        self,
        outcomes: Iterable[FileConversionOutcome],
        output_directory: Path,
    ) -> dict[str, Path]:
        """Return stable, collision-free output names for one export run."""
        targets: dict[str, Path] = {}
        reserved: set[str] = set()

        for outcome in outcomes:
            stem = outcome.source_path.stem
            suffix = 1
            target = output_directory / f"{stem}.md"
            while target.name.casefold() in reserved:
                suffix += 1
                target = output_directory / f"{stem} ({suffix}).md"

            reserved.add(target.name.casefold())
            targets[self._path_key(outcome.source_path)] = target

        return targets

    def _set_busy(self, busy: bool) -> None:
        self.cancel_button.setVisible(busy)
        self.progress.setVisible(busy)
        self.drop_zone.browse_button.setDisabled(busy)
        self.remove_button.setDisabled(busy)
        self.clear_button.setDisabled(busy)
        self.choose_output_button.setDisabled(busy)
        self.convert_button.setDisabled(busy)
        self.export_button.setDisabled(busy)

    def _update_actions(self) -> None:
        busy = self._thread is not None
        count = len(self._files)
        extension = self._files[0].suffix.upper() if self._files else ""
        label = f"{count} file{'s' if count != 1 else ''} selected"
        if extension:
            label += f" · {extension} batch"
        self.summary_label.setText(label)

        has_success = any(
            outcome.succeeded for outcome in self._outcomes.values()
        )
        self.convert_button.setEnabled(bool(self._files) and not busy)
        self.export_button.setVisible(has_success and not busy)
        self.export_button.setEnabled(has_success and not busy)
        self.remove_button.setEnabled(bool(self._files) and not busy)
        self.clear_button.setEnabled(bool(self._files) and not busy)
        self.copy_button.setEnabled(bool(self.preview.toPlainText()))

    def _reset_preview_if_needed(self) -> None:
        selected = self.file_tree.selectedItems()
        if selected:
            self._show_selected_preview()
            return
        self.preview.clear()
        self.preview_file.setText("Select a converted file")
        self.preview_summary.setText("No conversion result yet")

    def _show_error(self, message: str) -> None:
        self.error_banner.setText(message)
        self.error_banner.show()

    def _hide_error(self) -> None:
        self.error_banner.clear()
        self.error_banner.hide()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.information(
                self,
                "Conversion in progress",
                "Wait for the current conversion to finish before closing.",
            )
            event.ignore()
            return
        event.accept()
