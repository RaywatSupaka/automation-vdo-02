# Architecture

## Runtime boundaries

```text
React + TypeScript (frontend/)
           | authenticated loopback HTTP
FastAPI (api.py) ---- diagnostics.py / offline.py
           | commands + read models
Jobs service ---- SQLite: jobs / receipts / events
                       |
Worker process ---- Engine state transitions
                       |
                  Provider protocol
                       |
             Offline Simulator (only adapter in 0.1.0)
```

pywebview/WebView2 displays the same compiled UI. The desktop host owns API and worker lifetime.
The UI never directly edits the database or decides whether to replay a provider request.
Single application and worker file locks are scoped to the data directory. SQLite `BEGIN IMMEDIATE`
serializes commands and claims; the worker performs external work outside transactions.

## Durable workflow

Jobs: `queued -> running -> completed`, or `waiting`, `failed`, `needs_review`, `cancelled`.
Receipts: `prepared -> dispatching -> accepted -> completed`; uncertain outcomes become `unknown`.

The dispatch marker commits before submit. A crash while dispatching becomes review; prepared work can
resume and accepted work can only inspect its existing request. Reconciliation never calls submit.
Simulator requests are stored in a separate table to emulate an external acceptance surviving a crash;
their `sends` counter makes duplicate dispatch observable in tests. Real adapters will have external stores.

Safe pre-send availability failures retry at most 3 attempts. Result polling is bounded to 3 observations.
Artifact save retries at most 3 attempts while preserving the completed provider receipt. Explicit resume
after exhaustion can retry saving the same result. Auth requires user action; unknown sends require evidence.
Cancellation prevents subsequent stages, but a send already past its committed boundary may finish;
its receipt remains attached to the cancelled job.

The worker supervisor restarts at most 3 times per host session, then logs `WORKER_UNAVAILABLE`.
Each worker has its own one-way shutdown pipe and local Event. No synchronization lock is shared with
a killable worker. Parent death stops its worker. Forced shutdown preserves the durable receipt for recovery.
The simulator is immediate; future network/browser adapters MUST provide per-operation timeouts.

## Persistence and diagnostics

SQLAlchemy 2 + Alembic migration `0001`. WAL, foreign keys, busy timeout and FULL synchronous enabled.
Events and state changes commit together. Only committed events are mirrored into rotating JSON logs.
API and worker have separate files to avoid cross-process file rotation races (2 MB x 5 per role).
Events remain in SQLite for job history; automatic DB history pruning is not implemented in this foundation.
Media is outside SQLite. Save writes an owned temporary file, flushes it and atomically replaces the target.
Version 0.1.0 saves explicitly labelled simulator text checkpoints, not images or video.

Public diagnostics are fixed projections of status, IDs, codes and timings. No raw SQL endpoint exists.
Support ZIPs contain an allowlisted job snapshot and the latest 200 job events, with truncation indicated.
They omit title, prompt, provider result, credentials, local paths and raw DB. Internal exceptions record
class and filename/function/line frames without message, source text or locals.
Full private job data is only available to the authenticated local app; it is not part of support exports.

## API and isolation

Bind 127.0.0.1 only. Every `/api` route requires a session Bearer token, including OpenAPI and diagnostics.
Reject foreign Origin headers. Desktop passes its ephemeral token via URL fragment; UI moves it into
sessionStorage and removes the fragment. HTTP logs exclude URLs/query/input/header values.
No cloud upload or remote client access is enabled. Client support is an explicit local ZIP export.
The program and a diagnostic bundle do not grant an AI access to a client's machine.

## Extension points and release gaps

Implement real providers behind `Provider.preflight/submit/inspect`, with durable request ownership and
bounded calls. Browser Extension, actual Story/Product/Drama workflows, FFmpeg rendering, multi-scene
plans, automatic updater, installer/signing and remote support are not implemented yet.
Add their contracts and behavioral tests before enabling them; keep the simulator available for fast tests.
Future schema migrations must preserve customer data and define backup/restore compatibility before upgrade.

References: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[SQLAlchemy sessions](https://docs.sqlalchemy.org/en/20/orm/session_basics.html),
[pywebview packaging](https://pywebview.flowrl.com/guide/freezing.html).
