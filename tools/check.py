"""Focused checks, exact-name filtering and conservative changed-file selection."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from check_selection import ALL_SCOPES, PYTHON_SCOPES, changed_files, plan, select_scopes

ROOT = Path(__file__).resolve().parents[1]


def node_environment():
    env = os.environ.copy()
    local = sorted((ROOT / ".tools").glob("node-*-win-x64"))
    if local:
        env["PATH"] = str(local[-1]) + os.pathsep + env["PATH"]
    return env


def build_steps(scopes, npm, match=None):
    full = "all" in scopes
    selected = ["backend", "ui", "build-ui", "e2e"] if full else scopes
    steps = []
    if full:
        steps.append(
            (
                "lint",
                [sys.executable, "-m", "ruff", "check", "backend", "tests", "tools", "desktop_entry.py"],
                ROOT,
            )
        )
    paths = sorted({path for scope in selected for path in PYTHON_SCOPES.get(scope, [])})
    paths = [
        path for path in paths if not any(path.startswith(other + "/") for other in paths if other != path)
    ]
    if paths:
        label = "+".join(scope for scope in selected if scope in PYTHON_SCOPES)
        command = [sys.executable, "-m", "pytest", *paths]
        if match:
            command += ["-k", match]
        steps.append((label, command, ROOT))
    commands = {
        "ui": [npm, "test", *(["--", "-t", match] if match else [])],
        "typecheck": [npm, "exec", "--", "tsc", "-b"],
        "build-ui": [npm, "run", "build"],
        "e2e": [npm, "run", "test:e2e", *(["--", "--grep", match] if match else [])],
    }
    for scope in ("ui", "typecheck", "build-ui", "e2e"):
        if scope in selected and not (scope == "typecheck" and "build-ui" in selected):
            steps.append((scope, commands[scope], ROOT / "frontend"))
    if "desktop" in selected:
        steps.append(("desktop", [sys.executable, "tools/desktop_smoke.py"], ROOT))
    return steps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--scope", choices=ALL_SCOPES, nargs="+")
    mode.add_argument("--changed", action="store_true")
    parser.add_argument("--base", help="Git baseline for --changed; default includes local/untracked edits")
    parser.add_argument("--match", help="pytest -k / Vitest -t / Playwright --grep (one explicit scope)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--plan-json", type=Path)
    args = parser.parse_args()
    if args.base and not args.changed:
        parser.error("--base requires --changed")
    if args.match and (
        not args.scope or len(args.scope) != 1 or args.scope[0] not in [*PYTHON_SCOPES, "ui", "e2e"]
    ):
        parser.error("--match requires one Python, ui or e2e scope")
    paths = changed_files(ROOT, args.base) if args.changed else []
    summary = plan(select_scopes(paths) if args.changed else args.scope)
    summary.update(files=paths, match=args.match)
    env = node_environment()
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm", path=env["PATH"])
    steps = build_steps(summary["scopes"], npm, args.match)
    summary["steps"] = [{"scope": name, "command": cmd} for name, cmd, _ in steps]
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if args.plan_json:
        args.plan_json.parent.mkdir(parents=True, exist_ok=True)
        args.plan_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.dry_run or not steps:
        return 0
    results = []
    for name, command, cwd in steps:
        if not command[0]:
            parser.error("Node/npm missing. Run SETUP.bat")
        start = time.perf_counter()
        print(f"START {name}", flush=True)
        result = subprocess.run(command, cwd=cwd, env=env, check=False)
        results.append(
            {
                "scope": name,
                "command": command,
                "seconds": round(time.perf_counter() - start, 3),
                "exit_code": result.returncode,
            }
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
