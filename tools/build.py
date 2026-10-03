"""Build the portable Windows directory using the locked local toolchain."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from check import node_environment

ROOT = Path(__file__).resolve().parents[1]


def git_state(allow_dirty=False):
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    if dirty and not allow_dirty:
        print("Build refused: working tree is dirty; commit source first", file=sys.stderr)
        raise SystemExit(2)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return commit, dirty


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(target, commit, dirty, now):
    from smartflow import __version__

    config = json.loads(
        (target / "_internal" / "smartflow" / "bridge_config.json").read_text(encoding="utf-8")
    )
    extension = json.loads(
        (target / "extension" / "chrome-mv3" / "manifest.json").read_text(encoding="utf-8")
    )
    helper_version = config["helper_version"]
    extension_version = config["extension_version"]
    extension_manifest_version = extension["version"]
    if {__version__, helper_version, extension_version, extension_manifest_version} != {__version__}:
        raise ValueError("package version mismatch")
    return {
        "version": __version__,
        "app_version": __version__,
        "helper_version": helper_version,
        "extension_version": extension_version,
        "extension_manifest_version": extension_manifest_version,
        "source_commit": commit,
        "source_dirty": dirty,
        "built_at": now.isoformat(),
        "provider": "simulator",
        "exe_sha256": file_sha256(target / "SmartFlow Next.exe"),
        "helper_sha256": file_sha256(target / "helper" / "SmartFlowNextHost.exe"),
        "clean_machine_verified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)
    commit, dirty = git_state(args.allow_dirty)
    env = node_environment()
    npm = shutil.which("npm.cmd", path=env["PATH"])
    if not npm:
        raise RuntimeError("Run SETUP.bat first")
    subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", env=env, check=True)
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "packaging/smartflow.spec", "--noconfirm"], cwd=ROOT, check=True
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "packaging/helper.spec",
            "--noconfirm",
            "--distpath",
            str(ROOT / "build" / "helper-dist"),
            "--workpath",
            str(ROOT / "build" / "helper-work"),
        ],
        cwd=ROOT,
        check=True,
    )
    target = ROOT / "dist" / "SmartFlow Next"
    shutil.copytree(
        ROOT / "build" / "helper-dist" / "SmartFlowNextHost", target / "helper", dirs_exist_ok=True
    )
    subprocess.run([npm, "run", "build"], cwd=ROOT / "browser_extension", env=env, check=True)
    shutil.copytree(
        ROOT / "browser_extension" / ".output" / "chrome-mv3",
        target / "extension" / "chrome-mv3",
        dirs_exist_ok=True,
    )
    manifest = build_manifest(target, commit, dirty, datetime.now(timezone.utc))
    (target / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Built {target / 'SmartFlow Next.exe'}; keep all files in this directory together")


if __name__ == "__main__":
    main()
