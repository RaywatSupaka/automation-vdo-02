# P4 integration verification — 2026-10-03

## Scope and commits

Starting commit on `dev`: `0764193` (clean working tree). Last source commit: `39e4416`.
This verification file and its index link are committed as T6; use `git log -1 -- docs/delivery/verification-p4.md` for that commit.

| Task | Commit | Result |
|---|---|---|
| T1 | `b9b9fed` | Save the draft, then start an idempotent simulated Story job from its revision |
| T2 | `787f159` | Poll status with bounded read retries; show result and permission-gated commands |
| T3 | `98c32b8` | Show expected Extension and helper versions returned by the API |
| T4 | `decf38b` | E2E owner UI start through a paired simulated agent, result, and duplicate grant denial |
| T5 | `39e4416` | Isolate supervisor restart decisions and cover them with fake-process tests |

## Checks actually run

| Command | Result | Measured seconds |
|---|---|---:|
| `tools/check.py --scope ui typecheck` baseline | UI 86 passed; typecheck passed | UI 20.115; typecheck 38.554 |
| `tools/check.py --scope ui typecheck` T1 | UI 91 passed; typecheck passed | UI 1.783; typecheck 2.975 |
| `tools/check.py --scope ui typecheck` T2 | UI 94 passed; typecheck passed | UI 1.823; typecheck 2.536 |
| `tools/check.py --scope ui typecheck` T3 | UI 95 passed; typecheck passed | UI 1.760; typecheck 3.089 |
| `tools/check.py --scope build-ui` T4 | passed | 21.192 |
| `tools/check.py --scope e2e --match "story job"` | 1 passed | 23.524 |
| `tools/check.py --scope e2e` | 12 passed | 30.838 |
| `tools/check.py --scope unit runtime` baseline | lint passed; 60 passed | lint 3.494; tests 10.731 |
| `tools/check.py --scope unit runtime` T5 | lint passed; 64 passed | lint 0.147; tests 8.706 |
| `tools/check.py --scope all` final, once | lint passed; backend 238, UI 95, E2E 12, Extension unit 13 passed; both builds, typecheck and Extension smoke passed | 174.031 total |

Final `--scope all` step times: lint 0.147 s; backend 34.075 s; UI 11.949 s; UI build 36.345 s;
E2E 32.406 s; Extension unit 38.573 s; Extension typecheck 13.513 s; Extension build 3.441 s;
Extension smoke 3.582 s. The smoke test used its owned Chromium profile.

## Evidence by layer

- **Source UI and fixture E2E:** The new E2E creates a draft, starts a job from the review step, pairs a simulated agent through the test API, persists `[SIMULATION ONLY]` output, and checks the second grant is denied. All 12 Playwright tests passed against temporary test data on port 8788.
- **Dev desktop activation:** The existing `SmartFlow Next` window (PID 37748) closed through `CloseMainWindow()` and its process was absent after 20 seconds. `RUN_DEV.vbs` opened a new window (PID 26116). Its local page served `assets/index-BjdbwQOJ.js`, matching the final UI build. Native window content was not visually inspected by the available tools.
- **Real Chrome:** Not run. The agent could not operate the native Dev window to enter a test draft; this runbook step waits for the owner to click **เริ่มงานจำลอง**. No user Chrome profile, registry or Extension was changed.
- **Packaged EXE / clean Windows / real provider:** Not tested or built. The Story result is simulation text, not real media.

## Remaining work

Owner action: run the real Chrome trial from the Dev window and confirm a completed receipt for one new simulated job.
Provider adapters, real media, a packaged P4 EXE, clean-Windows validation, and an end-to-end stalled-worker restart test remain outside this handoff.

Source: [Story UI](../../frontend/src/features/story-shorts/StoryShorts.tsx),
[status polling](../../frontend/src/features/story-shorts/story-status.ts),
[supervisor](../../backend/smartflow/runtime.py).
Tests: [Story E2E](../../frontend/e2e/story-job.spec.ts),
[status unit](../../frontend/src/features/story-shorts/story-status.test.ts),
[supervisor unit](../../tests/unit/test_supervisor.py).
