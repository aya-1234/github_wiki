import subprocess
from pathlib import Path


class MacOSAdapter:
    def open_directory(self, path: Path) -> None:
        subprocess.run(["open", str(path)], check=True)
