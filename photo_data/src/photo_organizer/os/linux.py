import subprocess
from pathlib import Path


class LinuxAdapter:
    def open_directory(self, path: Path) -> None:
        subprocess.run(["xdg-open", str(path)], check=True)
