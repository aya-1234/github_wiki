import os
from pathlib import Path


class WindowsAdapter:
    def open_directory(self, path: Path) -> None:
        os.startfile(path)  # type: ignore[attr-defined]
