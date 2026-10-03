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
- **Real Chrome (owner trial, 2026-10-03):** The owner clicked **เริ่มงานจำลอง** in the Dev window for draft revision 14. The paired 0.2.0 Extension in the owner's Chrome profile claimed it 19.0 s after the snapshot; events were `story.snapshot_created` → `story.claimed` (19.0 s) → `story.dispatch_marked` (19.6 s, exactly once) → `story.result_collected` → `story.artifact_persisted` (20.2 s). Job `completed`, receipt `completed`, lease epoch 1. The artifact file's SHA-256 matches the receipt and its text equals `[SIMULATION ONLY]` + the snapshot topic. Runtime and worker logs contain neither the topic nor the result text. Checked read-only from the Dev database.
- **Packaged EXE / clean Windows / real provider:** Not tested or built. The Story result is simulation text, not real media.

## Remaining work

Owner real-Chrome trial: done (see Evidence by layer).
Provider adapters, real media, a packaged P4 EXE, clean-Windows validation, and an end-to-end stalled-worker restart test remain outside this handoff.

Source: [Story UI](../../frontend/src/features/story-shorts/StoryShorts.tsx),
[status polling](../../frontend/src/features/story-shorts/story-status.ts),
[supervisor](../../backend/smartflow/runtime.py).
Tests: [Story E2E](../../frontend/e2e/story-job.spec.ts),
[status unit](../../frontend/src/features/story-shorts/story-status.test.ts),
[supervisor unit](../../tests/unit/test_supervisor.py).

## งานสำรอง

ทำ B1–B5 ตามลำดับ โดยเพิ่มเทสให้เห็นความล้มเหลวกับโค้ดเดิมก่อนแก้แต่ละข้อ แล้ว commit แยกเรื่อง:

| งาน | Commit | ผล |
|---|---|---|
| B1 | `71a5721` | โหมด prod ปฏิเสธ scenario จำลองความผิดพลาดด้วย `SCENARIO_NOT_ALLOWED`; test mode ยังใช้ได้ |
| B2 | `3f85574` | `create_app()` และ runtime ใช้ migration guard เดียว; startup migrate ครั้งเดียว ทั้ง desktop และ CLI/API |
| B3 | `cde86e5` | pending pairing ที่หมดอายุกลายเป็น expired พร้อม event ใน transaction; revoke ซ้ำไม่มี event ซ้ำ |
| B4 | `f7a6cbe` | `issues()` ใช้ตัวอ่านเลขเดียวกับ `completeness()`/UI รวมรูปแบบเลขพิเศษ |
| B5 | `c3ce845` | UI จำกัด `maxFiles` ตาม registry และ persistence contract ตรวจค่าเหล่านี้ |

หลักฐาน red/green: B1 201 แทน 409 ก่อนแก้ (1.733 s), focused ผ่านหลังแก้ (1.628 s); B2 migrate 2 ครั้งแทน 1 (1.896 s), ผ่าน (1.942 s); B3 expiry ยัง pending (1.469 s) และ revoke log ซ้ำ (1.943 s), ผ่านแยกเคส (1.347/1.781 s); B4 ตัวเลข 3 เคสไม่ตรง UI (3.069 s), ผ่าน 5 เคส (2.129 s); B5 UI ยอมรับไฟล์เกินกำหนด (20.860 s) และ contract ขาด `maxFiles` (3.094 s), ผ่าน (1.969/2.590 s).

| คำสั่งตาม runbook | ผล | เวลาจริง |
|---|---|---:|
| `tools/check.py --scope workflow api` | 54 passed | 11.719 s |
| `tools/check.py --scope contracts migration runtime api-core` | 31 passed | 12.398 s |
| `tools/check.py --scope pairing auth` | 43 passed | 7.192 s |
| `tools/check.py --scope unit story-api story-workflow` | 119 passed | 20.437 s |
| `tools/check.py --scope ui typecheck` | UI 96 passed; typecheck passed | UI 3.271 s; typecheck 53.413 s |
| `tools/check.py --scope build-ui e2e` | build passed; E2E 12 passed | build 22.541 s; E2E 41.745 s |
| `tools/check.py --scope all` หลัง B1–B5, ครั้งเดียว | lint ผ่าน; backend 246, UI 96, E2E 12, Extension unit 13 ผ่าน; build/typecheck/smoke ผ่าน | 136.611 s รวมเวลารายขั้น |

`--scope all` รายขั้น: lint 0.160 s; backend 33.414 s; UI 3.237 s; UI build 6.632 s; E2E 33.415 s; Extension unit 39.889 s; Extension typecheck 13.967 s; Extension build 3.436 s; Extension smoke 2.461 s. Smoke ใช้ Chromium profile ของเทสเอง.

หลัง B5 ปิดหน้าต่าง Dev เดิม PID 26116 ด้วย `CloseMainWindow()` และตรวจว่าหายไปหลัง 20.272 s; เปิด `RUN_DEV.vbs` entry เดิมแล้วได้หน้าต่าง SmartFlow Next PID 42752 หลัง 15.328 s. หน้า local เสิร์ฟ `assets/index-B5ZB2nA7.js` ตรงกับ build ล่าสุด. ยังไม่ได้ตรวจภาพภายในหน้าต่างด้วยเครื่องมือ native UI. Real Chrome trial จากหน้าต่าง Dev ยังรอเจ้าของกด; ไม่มีการแก้ profile, registry หรือ Extension เดิม. ไม่ได้ build/test main EXE, clean Windows หรือ provider จริง และผล Story ทุกชิ้นยังเป็น `SIMULATION`.
