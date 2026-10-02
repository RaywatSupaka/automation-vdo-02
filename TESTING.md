# Testing

Use `.venv/Scripts/python.exe tools/check.py --scope <scope>`.
Each run prints elapsed wall time and saves a unique JSON result in ignored `build/checks/`.

| Change | Scope | Evidence |
|---|---|---|
| Error definitions, validation, locks, migration | unit | contracts + disposable SQLite |
| API, auth, exports, safe logs | api | real ASGI requests and temporary database |
| Job transitions, receipts, retry, cancellation | workflow | simulator, injected clock, no sleeps |
| Worker lifetime/supervisor | runtime | actual child process termination and recovery |
| UI actions | ui | Vitest action rules |
| UI/API interaction | e2e | Playwright + real local API + worker |
| Broad change / first handoff | all | lint + backend + UI + compiled UI + E2E |

Offline doctor tests: `.venv/Scripts/python.exe -m pytest tests/test_offline.py`.
Add the smallest relevant behavioral regression test and a duplicate/timing/crash variant where applicable.
Small edits use the scopes in this table, not every suite. Do not use real provider generations in normal tests.
Test duration targets: unit/workflow/API under 10s each; full foundation check under 60s after dependencies
are installed. These are local feedback budgets, not promises for CI provisioning or future real-media tests.

For E2E, build the UI first (`npm run build` in frontend), then `--scope e2e`.
`tools/setup.ps1` installs Playwright Chromium; E2E creates isolated data in the OS temporary directory.
Traces on failure and screenshots go to ignored `frontend/test-results/`. No real browser profile is used.

Test typescript via `npm run build`; Python style via `python -m ruff check backend tests tools desktop_entry.py`.
The current Starlette version emits an httpx TestClient deprecation warning; tests are functional.

## Packaged verification

Build using `tools/build.ps1`. Test with an isolated `SMARTFLOW_DATA_DIR` and unused port.
`SmartFlow Next.exe --desktop-smoke` creates one owned window, verifies React rendered in WebView2,
writes `desktop-smoke.json` in that isolated data directory, then closes its own window.
`tools/packaged_smoke.py` verifies compiled UI, API, worker, checkpoint and restart in the actual EXE.
Do not equate these with clean Windows, an installed extension or real provider output.

CI runs on Windows with cached dependencies. GitHub CI status is separate from local checks.
