import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_selection import changed_files, plan, select_scopes  # noqa: E402

spec = importlib.util.spec_from_file_location("smartflow_check_runner", ROOT / "tools/check.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.mark.parametrize(
    "paths,expected",
    [
        (["docs/index.md", "AGENTS.md"], []),
        (["backend/smartflow/auth.py"], ["unit-auth", "api"]),
        (["tests/test_auth.py"], ["auth"]),
        (["frontend/src/status.ts"], ["ui", "typecheck"]),
        (["frontend/src/App.tsx"], ["ui", "build-ui", "e2e"]),
        (["backend/smartflow/engine.py"], ["backend"]),
        (["backend/smartflow/new_module.py"], ["backend"]),
        (["new_service/unknown.py"], ["all"]),
        ([".github/workflows/checks.yml"], ["all"]),
        (["pyproject.toml"], ["all"]),
        (["backend\\smartflow\\auth.py", "tests/test_auth.py"], ["auth", "unit-auth", "api"]),
    ],
)
def test_selector_keeps_required_coverage(paths, expected):
    assert set(select_scopes(paths)) == set(expected)


def test_combined_python_scopes_collect_each_test_once():
    steps = runner.build_steps(["api", "auth", "unit", "unit-auth"], "npm")
    assert len(steps) == 1
    assert steps[0][1][3:] == ["tests/test_api.py", "tests/test_auth.py", "tests/unit"]
    assert len(runner.build_steps(["backend", "api"], "npm")) == 1
    assert runner.build_steps(["backend", "api"], "npm")[0][1][3:] == ["tests"]


def test_single_case_filter_and_full_gate_are_distinct():
    assert runner.build_steps(["auth"], "npm", "viewer")[0][1][-2:] == ["-k", "viewer"]
    assert runner.build_steps(["e2e"], "npm", "support")[0][1][-3:] == ["--", "--grep", "support"]
    assert [step[0] for step in runner.build_steps(["all"], "npm")] == [
        "lint",
        "backend",
        "ui",
        "build-ui",
        "e2e",
    ]
    assert not plan(["auth"])["needs_node"]
    assert not plan(["ui"])["needs_browser"]
    assert plan(["all"])["needs_browser"]


def test_changed_files_includes_staged_untracked_and_both_rename_paths(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "Fixture")
    (tmp_path / "old.py").write_text("before\n")
    git("add", ".")
    git("commit", "-qm", "fixture")
    base = git("rev-parse", "HEAD")
    git("mv", "old.py", "new.py")
    (tmp_path / "untracked.py").write_text("new\n")
    assert changed_files(tmp_path) == ["new.py", "old.py", "untracked.py"]
    assert changed_files(tmp_path, base) == ["new.py", "old.py"]
    assert select_scopes(changed_files(tmp_path, "0" * 40)) == ["all"]
