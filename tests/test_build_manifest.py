import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("smartflow_build", ROOT / "tools" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def package_files(tmp_path):
    target = tmp_path / "SmartFlow Next"
    (target / "helper").mkdir(parents=True)
    (target / "extension" / "chrome-mv3").mkdir(parents=True)
    (target / "_internal" / "smartflow").mkdir(parents=True)
    (target / "SmartFlow Next.exe").write_bytes(b"desktop executable")
    (target / "helper" / "SmartFlowNextHost.exe").write_bytes(b"native helper")
    (target / "extension" / "chrome-mv3" / "manifest.json").write_text(
        json.dumps({"version": "0.2.0"}), encoding="utf-8"
    )
    (target / "_internal" / "smartflow" / "bridge_config.json").write_text(
        json.dumps({"helper_version": "0.2.0", "extension_version": "0.2.0"}), encoding="utf-8"
    )
    return target


def test_build_manifest_contains_versions_and_executable_hashes(tmp_path):
    target = package_files(tmp_path)
    now = datetime(2026, 10, 3, 9, 0, tzinfo=timezone.utc)
    manifest = build.build_manifest(target, "a" * 40, False, now)
    assert manifest == {
        "version": "0.2.0",
        "app_version": "0.2.0",
        "helper_version": "0.2.0",
        "extension_version": "0.2.0",
        "extension_manifest_version": "0.2.0",
        "source_commit": "a" * 40,
        "source_dirty": False,
        "built_at": "2026-10-03T09:00:00+00:00",
        "provider": "simulator",
        "exe_sha256": hashlib.sha256(b"desktop executable").hexdigest(),
        "helper_sha256": hashlib.sha256(b"native helper").hexdigest(),
        "clean_machine_verified": False,
    }


@pytest.mark.parametrize("field", ["helper_version", "extension_version", "manifest_version"])
def test_build_manifest_rejects_version_mismatch(tmp_path, field):
    target = package_files(tmp_path)
    if field == "manifest_version":
        path = target / "extension" / "chrome-mv3" / "manifest.json"
        path.write_text(json.dumps({"version": "0.3.0"}), encoding="utf-8")
    else:
        path = target / "_internal" / "smartflow" / "bridge_config.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config[field] = "0.3.0"
        path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        build.build_manifest(target, "a" * 40, False, datetime.now(timezone.utc))


def test_dirty_source_is_rejected_before_build(monkeypatch, capsys):
    def fake_check_output(args, **_kwargs):
        if args[1] == "status":
            return " M tools/build.py\n"
        return "a" * 40 + "\n"

    monkeypatch.setattr(build.subprocess, "check_output", fake_check_output)
    with pytest.raises(SystemExit) as error:
        build.git_state()
    assert error.value.code == 2
    assert "dirty" in capsys.readouterr().err.lower()
    assert build.git_state(allow_dirty=True) == ("a" * 40, True)
