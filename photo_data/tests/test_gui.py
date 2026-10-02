import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from photo_organizer.config.settings import Settings
from photo_organizer.gui.main_window import MainWindow


def test_gui_starts_background_copy_and_shows_result(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    Image.new("RGB", (2, 2), "green").save(source / "photo.jpg")
    window = MainWindow(Settings(source_path=source, destination_path=destination))
    window.show()

    QTest.mouseClick(window.start_button, Qt.MouseButton.LeftButton)
    assert window.worker is not None
    assert window.worker.wait(10_000)
    app.processEvents()

    assert any(destination.rglob("photo.jpg"))
    assert "copied 1" in window.status.text()
    window.close()
