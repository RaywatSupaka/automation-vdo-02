import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_selection import PYTHON_SCOPES  # noqa: E402

spec = importlib.util.spec_from_file_location("smartflow_check_lint_runner", ROOT / "tools/check.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

RUFF = [sys.executable, "-m", "ruff", "check", "backend", "tests", "tools", "desktop_entry.py"]


def names(scopes, match=None):
    return [name for name, _, _ in runner.selected_steps(scopes, "npm", match)]


@pytest.mark.parametrize("scope", sorted(PYTHON_SCOPES))
def test_every_python_scope_lints_whole_repo_before_tests(scope):
    steps = runner.selected_steps([scope], "npm")
    assert steps[0] == ("lint", RUFF, ROOT)
    assert steps[1][1][1:3] == ["-m", "pytest"]


def test_lint_runs_once_for_combined_full_and_filtered_selections():
    assert names(["unit", "story-api", "ui"]) == ["lint", "unit+story-api", "ui"]
    assert names(["all"]).count("lint") == 1
    assert names(["all"])[0] == "lint"
    assert names(["auth"], "viewer") == ["lint", "auth"]
    assert runner.selected_steps(["auth"], "npm", "viewer")[1][1][-2:] == ["-k", "viewer"]


@pytest.mark.parametrize("scopes", [["ui"], ["typecheck"], ["extension-unit"], ["desktop"], []])
def test_non_python_selections_do_not_add_lint(scopes):
    assert "lint" not in names(scopes)


def test_dry_run_plan_reports_lint_step_without_running_it(tmp_path):
    plan_path = tmp_path / "plan.json"
    command = [sys.executable, "tools/check.py", "--scope", "unit", "--dry-run", "--plan-json", plan_path]
    subprocess.run(command, cwd=ROOT, check=True, capture_output=True, timeout=60)
    steps = json.loads(plan_path.read_text(encoding="utf-8"))["steps"]
    assert [step["scope"] for step in steps] == ["lint", "unit"]
    assert steps[0]["command"][1:] == RUFF[1:]
