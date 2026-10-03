# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**[AGENTS.md](AGENTS.md) holds the binding working rules. Read it first and follow it.** This file only adds orientation.

SmartFlow Next is a local-first Windows desktop app: React UI in a pywebview/WebView2 window, backed by a FastAPI + SQLite backend and a separate worker process on the same machine. There is no cloud backend. Release 0.1.0 uses a **simulator** provider only; never present simulator output as real media.

## Docs workflow

- Docs are written in Thai. Start at [docs/index.md](docs/index.md) and open only the row that matches the task. Do not bulk-read docs or source.
- One topic per doc. Update the owning doc in place and link it from the index. Never append history or reports to a central file.
- Work on branch `dev`. Check `git status` before editing and keep existing uncommitted work.

## Commands

Setup and launch (Windows, Python 3.11; Node 24 is installed into `.tools/` by setup):

```powershell
.\SETUP.bat
wscript.exe .\RUN_DEV.vbs   # Dev desktop, no console; defaults to dev_bypass auth (token/permission checks still enforced)
```

Use `.venv/Scripts/python.exe` for every Python command. All checks go through `tools/check.py`, which writes timing and JSON results to `build/checks/`:

```powershell
.venv/Scripts/python.exe tools/check.py --changed --dry-run        # show which scopes your changes select
.venv/Scripts/python.exe tools/check.py --scope unit-auth api-core  # several scopes, deduplicated into one pytest run
.venv/Scripts/python.exe tools/check.py --scope auth --match viewer # one case (pytest -k / vitest -t / playwright --grep)
.venv/Scripts/python.exe -m pytest tests/test_auth.py::test_missing_policy_fails_closed_before_handler
.venv/Scripts/python.exe -m ruff check backend tests tools desktop_entry.py
.venv/Scripts/python.exe tools/export_contract.py                   # regenerate contracts/openapi.json after any API change
```

[docs/development/testing.md](docs/development/testing.md) lists the scopes, for example `unit`, `contracts`, `api`, `story-api`, `migration`, `pairing`, `workflow`, `runtime`, `ui`, `typecheck`, `e2e`, `extension-unit`, `build-extension`, `extension-smoke`, `desktop`, `tooling` and `all`. File-to-scope mapping lives only in `tools/check_selection.py`; add a mapping when you add a feature. Unmapped files fall back to `all`. A `--match` that selects zero tests counts as a failure.

Frontend (`frontend/`): `npm run build` (runs `tsc -b`, then Vite), `npm test` (Vitest), `npm run test:e2e` (Playwright). `npm run dev` serves Vite on loopback and proxies `/api` to port 8766. The desktop window loads the **built** `dist`, so you must rebuild after a UI change, then close and reopen the desktop app as AGENTS.md describes.

Browser extension (`browser_extension/`, WXT MV3): `npm run build`, `npm run typecheck`, `npm test`.

## Architecture

```
React (frontend/src) --authenticated loopback HTTP--> FastAPI (api.py + *_routes.py)
   --> services (jobs.py, drafts.py, assets.py, browser_bridge.py) --> SQLite (db.py, Alembic)
Worker process (worker.py) --> engine.py --> providers.py (Provider protocol; simulator only)
Desktop host (desktop_entry.py, runtime.py): pywebview window plus API/worker lifetime supervision
Native messaging helper (native_entry.py, native_host.py) <--> browser_extension
```

- **Business rules belong in backend services.** They do not go in React components or desktop callbacks. The UI never writes to the DB and never decides whether to resend.
- **Auth:** `auth.py` defines the `Permission` and `Role` enums and the role → permission sets. Each route declares `openapi_extra=policy(Permission.X)`. A route with no policy is denied (fail closed). Browser agent and pairing roles get narrow scoped tokens. See `docs/operations/security.md`.
- **Storage:** SQLite runs in WAL mode with foreign keys on. Write transactions use `BEGIN IMMEDIATE`. State changes and their events commit in the same transaction and are mirrored to the log only after commit. No transaction stays open while waiting on an external call. Migrations are in `backend/smartflow/migrations/versions/` (numbered `000N_*.py`). `migration_safety.py` backs up the DB before an upgrade and refuses unknown versions. Media files live outside SQLite and are written with a temp file, fsync, then atomic replace.
- **Jobs and receipts:** every external operation persists a receipt before dispatch. An uncertain or accepted send is never auto-replayed. The supervisor restarts the worker at most 3 times per host session, then records `WORKER_UNAVAILABLE`. Application and worker locks are scoped per data directory.
- **Data directories:** Dev uses `.smartflow/`, EXE/prod uses `%LOCALAPPDATA%/SmartFlowNext`, and tests use a per-fixture temp directory. Configure with `SMARTFLOW_DATA_DIR`, `SMARTFLOW_MODE` (`dev`/`prod`/`test`) and `SMARTFLOW_PORT` (default 8766). Never point tests at real data.
- **Story Shorts drafts:** the draft model has ~95 fields, defined in `draft_fields.json` and `draft_contracts.py`. It supports revision conflicts, idempotent commands (`draft_commands`) and autosave with a flush on close (`desktop_close.py`). The UI is a shared step wizard in `frontend/src/components/step-wizard` plus `frontend/src/features/story-shorts`.
- **Errors and logging:** stable error codes are catalogued in `errors.py`. Logs are allowlisted through `observability.py`, so do not log tokens, prompts, provider output, titles, raw exception messages or user paths.
- **Contracts:** `contracts/openapi.json` is generated output and must stay in sync with the routes.
