"""Launch the actual no-console dev entry point in an isolated desktop session."""

import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    start = time.monotonic()
    directory = Path(tempfile.mkdtemp(prefix="smartflow-desktop-"))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = {
        **os.environ,
        "SMARTFLOW_DATA_DIR": str(directory),
        "SMARTFLOW_PORT": str(port),
        "SMARTFLOW_AUTH_MODE": "dev_bypass",
        "SMARTFLOW_SESSION_ROLE": "owner",
    }
    # Do not inherit credentials of a user-owned session.
    env.pop("SMARTFLOW_API_TOKEN", None)
    env.pop("SMARTFLOW_DIAGNOSTICS_TOKEN", None)
    subprocess.run(
        ["wscript.exe", str(ROOT / "RUN_DEV.vbs"), "--desktop-smoke"],
        env=env,
        cwd=ROOT,
        check=True,
        timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    marker = directory / "desktop-smoke.json"
    deadline = time.monotonic() + 45
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.2)
    if not marker.exists():
        raise RuntimeError("Desktop smoke failed; inspect isolated runtime log")
    report = json.loads(marker.read_text(encoding="utf-8"))
    assert report["dashboard_rendered"] and report["webview_loaded"]
    assert report["console_attached"] is False
    # The smoke window closes itself; wait for its API to close too.
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                break
        time.sleep(0.2)
    else:
        raise RuntimeError("Owned smoke desktop did not close")
    report["seconds"] = round(time.monotonic() - start, 3)
    target = ROOT / "build" / "desktop-smoke.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
