from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
)

from photo_organizer.config.settings import Settings


class SettingsWindow(QDialog):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.setWindowTitle("Settings")
        layout = QFormLayout(self)
        self.source = QLineEdit(str(settings.source_path or ""))
        self.destination = QLineEdit(str(settings.destination_path or ""))
        self.extensions = QLineEdit(", ".join(settings.supported_extensions))
        self.mode = QComboBox()
        self.mode.addItems(["copy", "move"])
        self.mode.setCurrentText(settings.default_mode)
        self.warning = QCheckBox("Warn before moving files")
        self.warning.setChecked(settings.move_warning)
        self.fallback = QComboBox()
        self.fallback.addItems(["file_mtime", "skip"])
        self.fallback.setCurrentText(settings.date_fallback)
        self.date_folders = QCheckBox("Create year/month/day folders")
        self.date_folders.setChecked(settings.create_date_folder)
        layout.addRow("Source", self.source)
        layout.addRow("Destination", self.destination)
        layout.addRow("Supported extensions", self.extensions)
        layout.addRow("Default mode", self.mode)
        layout.addRow("Date fallback", self.fallback)
        layout.addRow(self.warning)
        layout.addRow(self.date_folders)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _save(self) -> None:
        self.settings.source_path = Path(self.source.text()).expanduser() if self.source.text().strip() else None
        self.settings.destination_path = Path(self.destination.text()).expanduser() if self.destination.text().strip() else None
        self.settings.supported_extensions = tuple(part.strip() for part in self.extensions.text().split(",") if part.strip())
        self.settings.default_mode = self.mode.currentText()
        self.settings.move_warning = self.warning.isChecked()
        self.settings.date_fallback = self.fallback.currentText()
        self.settings.create_date_folder = self.date_folders.isChecked()
        self.settings.__post_init__()
        self.settings.save()
        self.accept()
