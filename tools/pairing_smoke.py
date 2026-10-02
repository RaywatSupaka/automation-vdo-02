"""Real Chrome/native EXE pairing in a private backend/profile/host registration."""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    import winreg

    start = time.monotonic()
    directory = Path(tempfile.mkdtemp(prefix="smartflow-pairing-smoke-"))
    source = ROOT / "build/native/SmartFlowNextHost"
    helper = directory / "helper"
    shutil.copytree(source, helper)
    executable = helper / "SmartFlowNextHost.exe"
    compat = json.loads((ROOT / "backend/smartflow/bridge_config.json").read_text())
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    host = "com.smartflow.next.smoke_" + uuid4().hex
    key_path = "Software\\Google\\Chrome\\NativeMessagingHosts\\" + host
    executable.with_suffix(".json").write_text(
        json.dumps(
            {
                "port": port,
                "extension_id": compat["extension_id"],
                "credential_path": str(directory / "agent.dpapi"),
            }
        ),
        encoding="utf-8",
    )
    manifest = directory / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "name": host,
                "description": "Owned SmartFlow pairing smoke",
                "path": str(executable),
                "type": "stdio",
                "allowed_origins": [f"chrome-extension://{compat['extension_id']}/"],
            }
        ),
        encoding="utf-8",
    )
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest))
    token = "owned-smoke-session-not-a-real-secret"
    env = {
        **os.environ,
        "SMARTFLOW_API_TOKEN": token,
        "SMARTFLOW_MODE": "test",
        "SMARTFLOW_AUTH_MODE": "local_session",
        "SMARTFLOW_SESSION_ROLE": "owner",
        "SMARTFLOW_DATA_DIR": str(directory / "data"),
    }
    env.pop("SMARTFLOW_DIAGNOSTICS_TOKEN", None)
    server = subprocess.Popen(
        [sys.executable, "-m", "smartflow.cli", "serve", "--port", str(port)],
        env=env,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        with httpx.Client(trust_env=False, timeout=1) as client:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    if client.get(f"http://127.0.0.1:{port}/").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Owned backend failed to start")
        node = next((ROOT / ".tools").glob("node-*/node.exe"))
        subprocess.run(
            [str(node), "tools/pairing_smoke.mjs", host, str(port), token], cwd=ROOT, check=True, timeout=60
        )
        assert (directory / "agent.dpapi").exists()
        result = {
            "chrome_native_exe_pairing": True,
            "credential_reused_by_new_host_process": True,
            "revocation_verified": True,
            "isolated_profile_and_host": True,
            "provider_tested": False,
            "seconds": round(time.monotonic() - start, 3),
        }
        (ROOT / "build/pairing-smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))
    finally:
        # Only the child process and unique registry key created by this smoke.
        server.terminate()
        server.wait(timeout=10)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            owned = winreg.QueryValue(key, None) == str(manifest)
        if owned:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)


if __name__ == "__main__":
    main()
