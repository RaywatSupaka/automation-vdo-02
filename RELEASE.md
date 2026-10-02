# Release status

Version: 0.1.0 foundation. Development branch: dev.

Implemented: local React desktop shell, authenticated FastAPI, SQLite migration, supervised worker,
durable simulator workflow, guarded resume/reconciliation, typed errors, logs, database diagnostics,
privacy-filtered support exports, offline doctor, tests and portable Windows build tooling.

Not implemented: real provider/Extension adapters, real video generation, Product/Story/Drama feature parity,
installer, code signing, automatic update and remote support. This release is for developing and evaluating
the new architecture; it is not a replacement for the existing customer application yet.

## Verified locally on 2026-10-02

- `tools/check.py --scope all`: passed. 32 backend tests in 4.57s; 2 Vitest tests;
  2 Playwright E2E tests in 8.6s. Total command wall time including lint, startup and UI build: 50.25s.
- Final lint passed; targeted browser rerun after UI work: 2 passed in 13.5s.
- One Starlette TestClient/httpx deprecation warning remains; no test failure in the completed full check.
- Initial development found a worker shutdown deadlock when a killed child shared a multiprocessing Event.
  The disposable pipe/local Event implementation passed the actual process-termination regression.
- Initial Vitest discovery also picked up Playwright files; explicit unit-test discovery fixed it.
- `tools/build.py`: portable Windows x64 directory built from clean source commit `5847f79`.
- `tools/packaged_smoke.py`: compiled UI, authenticated API, real worker process, persisted restart with
  one provider simulator send, automatic save recovery and native WebView2 dashboard all passed.
  The test used isolated data under a path containing Thai characters and closed its owned processes.
- EXE SHA-256: `88a78062c2b4f9b8ad9adeb35bcc5c794c053432406c932f67b60823276e1c3a`.
- Clean Windows/client installation, installer/signing, real providers and GitHub CI completion are unverified.

Generated binaries and local data are excluded from Git. Build manifests identify version, source commit,
dirty state and executable SHA-256. Documentation-only commits after `5847f79` do not change that tested binary.
