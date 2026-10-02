from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH).parent
data = [(str(root / "frontend" / "dist"), "web"),
        (str(root / "backend" / "smartflow" / "migrations"), "smartflow/migrations")]
data += collect_data_files("webview")
a = Analysis([str(root / "desktop_entry.py")], pathex=[str(root / "backend")],
    datas=data, hiddenimports=collect_submodules("uvicorn") + ["webview.platforms.edgechromium"],
    excludes=["pytest", "ruff", "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SmartFlow Next", debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="SmartFlow Next")
