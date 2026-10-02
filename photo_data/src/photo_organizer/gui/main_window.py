import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from photo_organizer.config.settings import Settings
from photo_organizer.core.organizer import Organizer
from photo_organizer.models.result import ProcessResult


class OrganizerWorker(QThread):
    progress = Signal(int, int, str, str)
    finished_result = Signal(object)
    failed = Signal(str)

    def __init__(self, settings: Settings, source: Path, destination: Path, mode: str) -> None:
        super().__init__()
        self.settings = settings
        self.source = source
        self.destination = destination
        self.mode = mode
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            result = Organizer(self.settings).run(
                self.source, self.destination, self.mode,
                progress=lambda current, total, path, status: self.progress.emit(current, total, str(path), status),
                cancelled=self.cancel_event.is_set,
            )
            self.finished_result.emit(result)
        except Exception as error:  # noqa: BLE001 — report worker failures in the GUI
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.worker: OrganizerWorker | None = None
        self.setWindowTitle("Photo Organizer")
        self.resize(640, 260)
        settings_menu = self.menuBar().addMenu("Settings")
        edit_settings = settings_menu.addAction("Preferences…")
        edit_settings.triggered.connect(self._open_settings)
        root = QWidget()
        layout = QVBoxLayout(root)
        self.source = QLineEdit(str(settings.source_path or ""))
        self.destination = QLineEdit(str(settings.destination_path or ""))
        layout.addLayout(self._path_row("Input", self.source))
        layout.addLayout(self._path_row("Destination", self.destination))
        modes = QHBoxLayout()
        self.copy_mode = QRadioButton("Copy")
        self.move_mode = QRadioButton("Move")
        (self.move_mode if settings.default_mode == "move" else self.copy_mode).setChecked(True)
        modes.addWidget(self.copy_mode)
        modes.addWidget(self.move_mode)
        layout.addLayout(modes)
        actions = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.start_button.clicked.connect(self._start)
        self.cancel_button.clicked.connect(self._cancel)
        actions.addWidget(self.start_button)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)
        self.progress = QProgressBar()
        self.status = QLabel("Ready")
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        self.setCentralWidget(root)

    @staticmethod
    def _path_row(label: str, field: QLineEdit) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(field)
        browse = QPushButton("Browse")
        browse.clicked.connect(lambda: field.setText(QFileDialog.getExistingDirectory(None, label) or field.text()))
        row.addWidget(browse)
        return row

    def _start(self) -> None:
        source, destination = Path(self.source.text()), Path(self.destination.text())
        mode = "move" if self.move_mode.isChecked() else "copy"
        if mode == "move" and self.settings.move_warning:
            answer = QMessageBox.warning(
                self, "Move photos?", "Files are removed from the source after successful transfer.",
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.worker = OrganizerWorker(self.settings, source, destination, mode)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished_result.connect(self._finished)
        self.worker.failed.connect(self._failed)
        self.worker.start()
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

    def _open_settings(self) -> None:
        from photo_organizer.gui.settings_window import SettingsWindow

        SettingsWindow(self.settings).exec()

    def _cancel(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.status.setText("Cancelling after current file…")
            self.cancel_button.setEnabled(False)

    def _update_progress(self, current: int, total: int, filename: str, status: str) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(current)
        self.status.setText(f"{filename} — {current}/{total} ({status})")

    def _finished(self, result: ProcessResult) -> None:
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status.setText(f"Processed {result.processed}; copied {result.copied}; moved {result.moved}; skipped {result.skipped}; errors {result.errors}")

    def _failed(self, message: str) -> None:
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        QMessageBox.critical(self, "Photo Organizer", message)


def launch(settings: Settings) -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings)
    window.show()
    return app.exec()
