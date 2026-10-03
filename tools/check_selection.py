"""Conservative changed-file selection. Unknown files fall back to full checks."""

import subprocess
from fnmatch import fnmatchcase

PYTHON_SCOPES = {
    "story-workflow": ["tests/test_story_workflow.py"],
    "story-api": ["tests/test_drafts.py", "tests/test_assets_pairing.py", "tests/test_asset_clock.py"],
    "pairing": ["tests/test_assets_pairing.py", "tests/test_native_host.py"],
    "migration": ["tests/test_migration_safety.py", "tests/test_contracts.py", "tests/test_offline.py"],
    "bridge-contract": ["tests/test_native_host.py"],
    "unit": ["tests/unit"],
    "unit-close": ["tests/unit/test_desktop_close.py"],
    "unit-auth": ["tests/unit/test_auth_policy.py"],
    "unit-input": ["tests/unit/test_inputs.py"],
    "contracts": ["tests/test_contracts.py"],
    "auth": ["tests/test_auth.py"],
    "api-core": ["tests/test_api.py"],
    "api": ["tests/test_api.py", "tests/test_auth.py"],
    "workflow": ["tests/test_workflow.py"],
    "runtime": ["tests/test_runtime.py"],
    "offline": ["tests/test_offline.py"],
    "tooling": ["tests/test_check_tools.py", "tests/test_check_lint.py", "tests/test_build_manifest.py"],
    "backend": ["tests"],
}
ALL_SCOPES = [
    *PYTHON_SCOPES,
    "ui",
    "typecheck",
    "build-ui",
    "extension-unit",
    "build-extension",
    "extension-smoke",
    "e2e",
    "desktop",
    "all",
]
RULES = [
    ("*.md", []),
    (".claude/*", []),  # Claude Code settings and hooks; no runtime boundary.
    ("backend/smartflow/story_*", ["story-workflow", "auth", "bridge-contract"]),
    ("tests/test_story_workflow.py", ["story-workflow"]),
    ("tests/test_assets_pairing.py", ["pairing", "story-api"]),
    ("backend/smartflow/asset*", ["story-api", "auth"]),
    ("backend/smartflow/*bridge*", ["pairing", "auth", "extension-unit"]),
    ("backend/smartflow/native_client.py", ["pairing"]),
    ("backend/smartflow/protected_store.py", ["pairing"]),
    ("backend/smartflow/desktop_close.py", ["unit-close"]),
    ("tests/test_drafts.py", ["story-api"]),
    ("tests/test_asset_clock.py", ["story-api"]),
    ("tests/test_migration_safety.py", ["migration"]),
    ("tests/test_native_host.py", ["bridge-contract"]),
    ("backend/smartflow/draft_fields.json", ["story-api", "unit", "ui"]),
    ("backend/smartflow/draft_contracts.py", ["story-api", "auth", "unit"]),
    ("backend/smartflow/draft*", ["story-api", "auth"]),
    ("backend/smartflow/migration*", ["migration", "story-api"]),
    ("backend/smartflow/native_host.py", ["bridge-contract", "extension-unit"]),
    ("browser_extension/*", ["extension-unit", "build-extension", "bridge-contract"]),
    ("tests/unit/*", ["unit"]),
    ("tests/test_auth.py", ["auth"]),
    ("tests/test_api.py", ["api-core"]),
    ("tests/test_contracts.py", ["contracts"]),
    ("tests/test_workflow.py", ["workflow"]),
    ("tests/test_runtime.py", ["runtime"]),
    ("tests/test_offline.py", ["offline"]),
    ("tests/test_check_tools.py", ["tooling"]),
    ("tests/test_check_lint.py", ["tooling"]),
    ("tests/test_build_manifest.py", ["tooling"]),
    ("tools/build.py", ["tooling"]),
    ("packaging/*", ["tooling"]),
    ("tools/register_native_host.py", ["unit"]),
    ("tests/conftest.py", ["backend"]),
    ("tools/check*.py", ["tooling"]),
    ("backend/smartflow/auth.py", ["unit-auth", "api"]),
    ("backend/smartflow/api.py", ["api"]),
    ("backend/smartflow/contracts.py", ["api"]),
    ("contracts/openapi.json", ["api"]),
    ("backend/smartflow/errors.py", ["unit", "api", "workflow"]),
    ("backend/smartflow/offline.py", ["offline"]),
    ("backend/smartflow/diagnostics.py", ["api-core", "offline"]),
    ("backend/smartflow/observability.py", ["api", "workflow", "offline"]),
    ("backend/smartflow/runtime.py", ["contracts", "runtime"]),
    ("backend/smartflow/worker.py", ["runtime", "workflow"]),
    ("backend/smartflow/cli.py", ["backend", "build-ui", "e2e"]),
    ("backend/smartflow/*.py", ["backend"]),
    ("frontend/src/status*", ["ui", "typecheck"]),
    ("frontend/*", ["ui", "build-ui", "e2e"]),
]


def select_scopes(paths):
    scopes = set()
    for path in paths:
        path = path.replace("\\", "/")
        for pattern, affected in RULES:
            if fnmatchcase(path, pattern):
                scopes.update(affected)
                break
        else:
            return ["all"]
    return [scope for scope in ALL_SCOPES if scope in scopes]


def changed_files(root, base=None):
    if base and set(base) == {"0"}:  # First push has no comparable parent.
        return ["<initial-push>"]
    # Disabling rename detection includes both deleted and added paths.
    args = ["git", "diff", "--no-renames", "--name-only", "-z", base or "HEAD"]
    data = subprocess.check_output(args, cwd=root).decode("utf-8")
    paths = [path for path in data.split("\0") if path]
    if not base:
        extra = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root
        ).decode("utf-8")
        paths.extend(path for path in extra.split("\0") if path)
    return sorted(set(paths))


def plan(scopes):
    selected = list(dict.fromkeys(scopes))
    if "all" in selected:
        selected = ["all"]
    browser = any(scope in selected for scope in ("all", "e2e", "extension-smoke"))
    return {
        "scopes": selected,
        "needs_node": browser
        or any(s in selected for s in ("ui", "typecheck", "build-ui", "extension-unit", "build-extension")),
        "needs_browser": browser,
        "needs_extension": "all" in selected
        or any(s in selected for s in ("extension-unit", "build-extension", "extension-smoke")),
        "has_checks": bool(selected),
    }
