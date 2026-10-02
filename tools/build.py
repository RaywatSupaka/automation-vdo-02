"""Build the portable Windows directory using the locked local toolchain."""

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from check import node_environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    import shutil

    from smartflow import __version__

    env = node_environment()
    npm = shutil.which("npm.cmd", path=env["PATH"])
    if not npm:
        raise RuntimeError("Run SETUP.bat first")
    subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", env=env, check=True)
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "packaging/smartflow.spec", "--noconfirm"], cwd=ROOT, check=True
    )
    target = ROOT / "dist" / "SmartFlow Next"
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    manifest = {
        "version": __version__,
        "source_commit": commit,
        "source_dirty": dirty,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "provider": "simulator",
        "exe_sha256": hashlib.sha256((target / "SmartFlow Next.exe").read_bytes()).hexdigest(),
        "clean_machine_verified": False,
    }
    (target / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Built {target / 'SmartFlow Next.exe'}; keep all files in this directory together")


if __name__ == "__main__":
    main()
