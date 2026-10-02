"""Small, explicit test scopes with one timing summary; no provider calls."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def node_environment():
    env = os.environ.copy()
    local = sorted((ROOT / ".tools").glob("node-*-win-x64"))
    if local:
        env["PATH"] = str(local[-1]) + os.pathsep + env["PATH"]
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope", choices=["unit", "api", "workflow", "runtime", "ui", "e2e", "all"], required=True
    )
    args = parser.parse_args()
    env = node_environment()
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm", path=env["PATH"])
    groups = {
        "unit": [("unit", [sys.executable, "-m", "pytest", "tests/test_contracts.py"], ROOT)],
        "api": [("api", [sys.executable, "-m", "pytest", "tests/test_api.py"], ROOT)],
        "workflow": [("workflow", [sys.executable, "-m", "pytest", "tests/test_workflow.py"], ROOT)],
        "runtime": [("runtime", [sys.executable, "-m", "pytest", "tests/test_runtime.py"], ROOT)],
        "ui": [("ui", [npm, "test"], ROOT / "frontend")],
        "e2e": [("e2e", [npm, "run", "test:e2e"], ROOT / "frontend")],
    }
    if args.scope == "all":
        steps = [
            (
                "lint",
                [sys.executable, "-m", "ruff", "check", "backend", "tests", "tools", "desktop_entry.py"],
                ROOT,
            ),
            ("backend", [sys.executable, "-m", "pytest"], ROOT),
            ("ui", [npm, "test"], ROOT / "frontend"),
            ("build-ui", [npm, "run", "build"], ROOT / "frontend"),
            *groups["e2e"],
        ]
    else:
        steps = groups[args.scope]
    results = []
    for name, command, cwd in steps:
        if not command[0]:
            parser.error("Node/npm missing. Run tools/setup.ps1")
        start = time.perf_counter()
        print(f"START {name}", flush=True)
        result = subprocess.run(command, cwd=cwd, env=env, check=False)
        results.append(
            {"scope": name, "seconds": round(time.perf_counter() - start, 3), "exit_code": result.returncode}
        )
        print(json.dumps(results[-1]), flush=True)
        if result.returncode:
            break
    output = ROOT / "build" / "checks"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{time.time_ns()}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results[-1]["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
