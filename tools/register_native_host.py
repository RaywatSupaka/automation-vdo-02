"""Register only SmartFlow Next's separate current-user native host."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOSTS_KEY = "Software\\Google\\Chrome\\NativeMessagingHosts\\"


class OwnershipError(RuntimeError):
    """The host name already points at a manifest this run did not create."""


class WindowsRegistry:
    """HKCU default value access for one key; tests inject a fake instead."""

    def __init__(self):
        import winreg

        self.winreg = winreg

    def read(self, key_path):
        try:
            with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, key_path) as key:
                return self.winreg.QueryValue(key, None)
        except FileNotFoundError:
            return None

    def write(self, key_path, value):
        with self.winreg.CreateKey(self.winreg.HKEY_CURRENT_USER, key_path) as key:
            self.winreg.SetValueEx(key, "", 0, self.winreg.REG_SZ, value)

    def delete(self, key_path):
        try:
            self.winreg.DeleteKey(self.winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            return False
        return True


def load_compat():
    return json.loads((ROOT / "backend/smartflow/bridge_config.json").read_text(encoding="utf-8"))


def host_key(compat):
    # Only this project's host name; never a parent key or another product's host.
    return HOSTS_KEY + compat["host_name"]


def register(executable, port, data_dir, replace=False, registry=None, compat=None, out=print):
    registry = WindowsRegistry() if registry is None else registry
    compat = load_compat() if compat is None else compat
    executable = Path(executable).resolve(strict=True)
    manifest = executable.parent / "native-manifest.json"
    key_path = host_key(compat)
    current = registry.read(key_path)
    if current is not None and Path(current).resolve() != manifest:
        if not replace:
            raise OwnershipError(
                "Another installation owns this host registration; rerun with --replace to move it here"
            )
        # Operator-run console output only, so the owner can see what is being moved.
        out(f"Replacing host registration: {current} -> {manifest}")
    config = {
        "port": port,
        "extension_id": compat["extension_id"],
        "credential_path": str(Path(data_dir).resolve() / "browser-agent.dpapi"),
    }
    executable.with_suffix(".json").write_text(json.dumps(config), encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "name": compat["host_name"],
                "description": "SmartFlow Next native bridge",
                "path": str(executable),
                "type": "stdio",
                "allowed_origins": [f"chrome-extension://{compat['extension_id']}/"],
            }
        ),
        encoding="utf-8",
    )
    registry.write(key_path, str(manifest))
    out("Registered SmartFlow Next host for the current Windows user")


def unregister(registry=None, compat=None, out=print):
    registry = WindowsRegistry() if registry is None else registry
    removed = registry.delete(host_key(load_compat() if compat is None else compat))
    # Manifest and config files stay on disk; only the registration key is removed.
    out(
        "Removed SmartFlow Next host registration for the current Windows user"
        if removed
        else "SmartFlow Next host is not registered for the current Windows user"
    )
    return removed


def main(argv=None, registry=None, compat=None, out=print):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".smartflow")
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--replace", action="store_true", help="move this host name from another manifest path to --exe"
    )
    action.add_argument("--unregister", action="store_true", help="remove only this host name's HKCU key")
    args = parser.parse_args(argv)
    if args.unregister:
        if args.exe:
            parser.error("--unregister does not take --exe")
        unregister(registry, compat, out)
        return 0
    if not args.exe:
        parser.error("--exe is required unless --unregister is used")
    try:
        register(args.exe, args.port, args.data_dir, args.replace, registry, compat, out)
    except OwnershipError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
