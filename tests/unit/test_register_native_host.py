import importlib.util
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "smartflow_register_host", ROOT / "tools/register_native_host.py"
)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
Adapter = tool.WindowsRegistry

COMPAT = {"host_name": "com.smartflow.fixture_host", "extension_id": "a" * 32}
KEY = tool.HOSTS_KEY + COMPAT["host_name"]
NEIGHBOUR = tool.HOSTS_KEY + "com.other.product"


class FakeRegistry:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.calls = []

    def read(self, key_path):
        self.calls.append(("read", key_path))
        return self.values.get(key_path)

    def write(self, key_path, value):
        self.calls.append(("write", key_path))
        self.values[key_path] = value

    def delete(self, key_path):
        self.calls.append(("delete", key_path))
        return self.values.pop(key_path, None) is not None


@pytest.fixture(autouse=True)
def no_real_registry(monkeypatch):
    def refuse():
        raise AssertionError("tests must never open the real Windows registry")

    monkeypatch.setattr(tool, "WindowsRegistry", refuse)


@pytest.fixture
def helper(tmp_path):
    executable = tmp_path / "new" / "SmartFlowNextHost.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"fixture")
    return executable


def run(registry, *argv):
    lines = []
    code = tool.main([*map(str, argv)], registry=registry, compat=COMPAT, out=lines.append)
    return code, lines


def test_fresh_and_repeated_registration_point_only_this_host_at_new_manifest(tmp_path, helper):
    registry = FakeRegistry({NEIGHBOUR: "C:/elsewhere/manifest.json"})
    for _ in range(2):  # Re-registering the same helper is not an ownership conflict.
        code, _ = run(registry, "--exe", helper, "--data-dir", tmp_path / "data")
        assert code == 0
    manifest = helper.parent / "native-manifest.json"
    assert registry.values == {NEIGHBOUR: "C:/elsewhere/manifest.json", KEY: str(manifest)}
    assert json.loads(manifest.read_text(encoding="utf-8"))["path"] == str(helper.resolve())
    assert {key for _, key in registry.calls} == {KEY}


def test_default_refuses_other_owner_without_writing_anything(tmp_path, helper, capsys):
    old = str(tmp_path / "old" / "native-manifest.json")
    registry = FakeRegistry({KEY: old})
    code, lines = run(registry, "--exe", helper)
    assert code == 2 and lines == []
    assert "--replace" in capsys.readouterr().err
    assert registry.values == {KEY: old}
    assert ("write", KEY) not in registry.calls
    assert not (helper.parent / "native-manifest.json").exists()
    assert not helper.with_suffix(".json").exists()
    with pytest.raises(tool.OwnershipError):
        tool.register(helper, 8766, tmp_path, registry=registry, compat=COMPAT, out=lines.append)


def test_replace_prints_old_and_new_then_moves_only_this_host_key(tmp_path, helper):
    old = str(tmp_path / "old" / "native-manifest.json")
    registry = FakeRegistry({KEY: old, NEIGHBOUR: "C:/elsewhere/manifest.json"})
    code, lines = run(registry, "--exe", helper, "--replace")
    manifest = helper.parent / "native-manifest.json"
    assert code == 0
    assert lines[0] == f"Replacing host registration: {old} -> {manifest}"
    assert registry.values == {KEY: str(manifest), NEIGHBOUR: "C:/elsewhere/manifest.json"}
    assert {key for _, key in registry.calls} == {KEY}
    assert manifest.is_file() and helper.with_suffix(".json").is_file()


def test_unregister_removes_only_this_host_and_repeat_is_noop(helper):
    registry = FakeRegistry({KEY: str(helper.parent / "native-manifest.json"), NEIGHBOUR: "keep"})
    code, first = run(registry, "--unregister")
    assert code == 0 and first == ["Removed SmartFlow Next host registration for the current Windows user"]
    code, second = run(registry, "--unregister")
    assert code == 0 and second == ["SmartFlow Next host is not registered for the current Windows user"]
    assert registry.values == {NEIGHBOUR: "keep"}
    assert registry.calls == [("delete", KEY), ("delete", KEY)]


@pytest.mark.parametrize(
    "argv",
    [[], ["--replace"], ["--unregister", "--replace"], ["--unregister", "--exe", "host.exe"]],
)
def test_invalid_command_lines_fail_before_registry_access(argv):
    registry = FakeRegistry({KEY: "kept"})
    with pytest.raises(SystemExit) as exit_info:
        run(registry, *argv)
    assert exit_info.value.code == 2
    assert registry.calls == [] and registry.values == {KEY: "kept"}


def test_winreg_adapter_maps_missing_key_to_none_and_false(monkeypatch):
    store = {}

    @contextmanager
    def open_key(root, path):
        if path not in store:
            raise FileNotFoundError
        yield path

    @contextmanager
    def create_key(root, path):
        store.setdefault(path, None)
        yield path

    def delete_key(root, path):
        if path not in store:
            raise FileNotFoundError
        del store[path]

    fake = SimpleNamespace(
        HKEY_CURRENT_USER="HKCU",
        REG_SZ=1,
        OpenKey=open_key,
        QueryValue=lambda key, sub: store[key],
        CreateKey=create_key,
        SetValueEx=lambda key, name, reserved, kind, value: store.__setitem__(key, value),
        DeleteKey=delete_key,
    )
    monkeypatch.setitem(sys.modules, "winreg", fake)
    adapter = Adapter()
    assert adapter.read(KEY) is None
    adapter.write(KEY, "manifest.json")
    assert adapter.read(KEY) == "manifest.json"
    assert adapter.delete(KEY) is True
    assert adapter.delete(KEY) is False and store == {}
