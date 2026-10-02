"""Windows bootstrap, without changing system Python, Node or execution policy."""

import hashlib
import os
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_VERSION = "v24.21.0"


def main():
    python = ROOT / ".venv/Scripts/python.exe"
    if not python.exists():
        subprocess.run(["py", "-3.11", "-m", "venv", str(ROOT / ".venv")], check=True)
    node_root = ROOT / ".tools" / f"node-{NODE_VERSION}-win-x64"
    if not (node_root / "node.exe").exists():
        node_root.parent.mkdir(exist_ok=True)
        filename = f"node-{NODE_VERSION}-win-x64.zip"
        base = f"https://nodejs.org/dist/{NODE_VERSION}/"
        archive = node_root.parent / filename
        urllib.request.urlretrieve(base + filename, archive)
        with urllib.request.urlopen(base + "SHASUMS256.txt", timeout=30) as response:
            rows = response.read().decode().splitlines()
        expected = next(row.split()[0] for row in rows if row.endswith(" " + filename))
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Node checksum mismatch")
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(node_root.parent)
    subprocess.run(
        [str(python), "-m", "pip", "install", "-c", "requirements.lock.txt", "-e", ".[dev,desktop]"],
        cwd=ROOT,
        check=True,
    )
    env = {**os.environ, "PATH": str(node_root) + os.pathsep + os.environ["PATH"]}
    npm = str(node_root / "npm.cmd")
    for args in (["ci"], ["run", "build"], ["exec", "--", "playwright", "install", "chromium"]):
        subprocess.run([npm, *args], cwd=ROOT / "frontend", env=env, check=True)
    print("Ready: open RUN_DEV.bat")


if __name__ == "__main__":
    main()
