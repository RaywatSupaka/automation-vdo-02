"""Register only SmartFlow Next's separate current-user native host."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def register(executable, port, data_dir):
    import winreg

    compat = json.loads((ROOT / "backend/smartflow/bridge_config.json").read_text())
    executable = executable.resolve(strict=True)
    directory = executable.parent
    manifest = directory / "native-manifest.json"
    key_path = "Software\\Google\\Chrome\\NativeMessagingHosts\\" + compat["host_name"]
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            old = Path(winreg.QueryValue(key, None)).resolve()
            if old != manifest:
                raise RuntimeError("Another installation owns this host registration")
    except FileNotFoundError:
        pass
    config = {
        "port": port,
        "extension_id": compat["extension_id"],
        "credential_path": str(data_dir.resolve() / "browser-agent.dpapi"),
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
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest))
    print("Registered SmartFlow Next host for the current Windows user")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".smartflow")
    args = parser.parse_args()
    register(args.exe, args.port, args.data_dir)
