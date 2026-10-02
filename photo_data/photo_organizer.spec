# PyInstaller entry point and dependency collection for Qt/Pillow.
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("PIL")
hiddenimports += [
    "photo_organizer.gui.main_window",
    "photo_organizer.gui.settings_window",
]

a = Analysis(
    ["src/photo_organizer/main.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="PhotoOrganizer", console=True)
