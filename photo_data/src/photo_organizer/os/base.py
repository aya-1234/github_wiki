from pathlib import Path
from typing import Protocol


class OSAdapter(Protocol):
    def open_directory(self, path: Path) -> None: ...


def get_adapter() -> OSAdapter:
    import platform

    system = platform.system()
    if system == "Windows":
        from photo_organizer.os.windows import WindowsAdapter

        return WindowsAdapter()
    if system == "Darwin":
        from photo_organizer.os.macos import MacOSAdapter

        return MacOSAdapter()
    from photo_organizer.os.linux import LinuxAdapter

    return LinuxAdapter()
