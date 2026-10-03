# P4 troubleshooting: เจอ error แล้วทำอะไร

ใช้คู่กับ [P4 execution plan](p4-integration.md) และ [คู่มือคำสั่ง](p4-runbook.md)
หลักใหญ่: อ่าน error ให้จบก่อน แก้ทีละอย่าง รันเฉพาะเทสที่ล้มซ้ำ ถ้าแก้ 2 รอบแล้วยังล้ม หยุดและรายงานพร้อมข้อความ error

## ก่อนแก้อะไร ให้ถามตัวเอง 3 ข้อ

1. ไฟล์ที่ล้มเป็นไฟล์ที่ฉันแก้ไหม (`git diff --stat`) ถ้าไม่ใช่และฉันไม่ได้แตะสิ่งที่มันใช้ → ไม่ใช่งานของฉัน รายงาน
2. error บอก code อะไร (เช่น `DRAFT_REVISION_CONFLICT`) หาในตารางด้านล่างก่อน
3. ถ้าจะแก้เทสเดิมให้ผ่าน ต้องมีเหตุผลว่าพฤติกรรมตั้งใจเปลี่ยน ห้ามลบ assertion เพื่อให้ผ่าน

## Build / lint / type

| อาการ | สาเหตุที่พบบ่อย | ทำอย่างไร |
|---|---|---|
| `tsc` error `Property 'flush' does not exist` | ยังไม่ได้เพิ่มใน `useDraft()` | ทำ T1 ข้อ 1 ก่อน |
| `tsc` error เรื่อง type ไม่ตรง | type ใน `api.ts` ไม่ครบ | เพิ่ม type ให้ตรง response จริง ห้ามใช้ `any` |
| `ruff` I001 import order | import ไม่เรียง | `ruff check --fix <ไฟล์>` แล้ว `ruff format <ไฟล์>` |
| `npm`/`node` not found | ไม่ได้ใช้ node ของโปรเจกต์ | รันผ่าน `tools/check.py` เสมอ (ใช้ `.tools/node-v24.21.0-win-x64`) |
| `--match` แล้ว "no tests" = fail | ชื่อเคสไม่ตรง | เปิดไฟล์เทสดูชื่อจริงใน `it('...')`/`def test_...` |
| bash: `unexpected EOF while looking for matching` | heredoc/quote ยาวพัง | เขียนสคริปต์ลงไฟล์ใน temp แล้วรัน `python <ไฟล์>` |

## Vitest / pytest

| อาการ | ทำอย่างไร |
|---|---|
| เทสที่ไม่ได้แตะล้ม | `git log -1 -- <ไฟล์เทส>` และ `git diff --stat` ถ้าไม่เกี่ยวกับงาน → รายงาน ไม่แก้ |
| เทส timer ค้าง/หมดเวลา | ใช้ `vi.useFakeTimers()` และ `await vi.advanceTimersByTimeAsync(ms)`; คืน `vi.useRealTimers()` ใน `afterEach` |
| `test_api.py::test_all_json_response_contracts_and_saved_openapi` ล้ม | เปลี่ยน API โดยไม่ตั้งใจ → ย้อนส่วนนั้น; ตั้งใจเปลี่ยน → `python tools/export_contract.py` แล้วตรวจ diff ว่ามีแต่ของตัวเอง |
| `test_auth.py` role matrix ล้ม | route ใหม่ไม่มี `openapi_extra=policy(...)` → เพิ่ม และเพิ่มเทส allow/deny |
| `database is locked` ในเทส | มี process อื่นถือ DB ของเทส → รันซ้ำหนึ่งครั้ง ถ้ายังล้ม รายงาน (ห้าม kill process ที่ไม่รู้จัก) |

## E2E (Playwright)

| อาการ | ทำอย่างไร |
|---|---|
| `port 8788 is already used` | `PS> Get-NetTCPConnection -LocalPort 8788 \| Select OwningProcess` แล้วดู CommandLine; ถ้าเป็น `smartflow.cli serve --port 8788` จากโปรเจกต์นี้ที่ค้าง ปิดได้ อย่างอื่นห้ามปิด → รายงาน |
| หาปุ่ม/ข้อความไม่เจอ | ถ้าแก้ `frontend/src` หลัง build ครั้งล่าสุด → `--scope build-ui` แล้ว `--scope e2e --match "<เคสที่ล้ม>"`; ดู trace ใน `frontend/test-results/` |
| ข้อความไม่ตรงทั้งหมด (`toHaveText`) | มีข้อความอื่นปนใน element เดียวกัน → ใช้ `toContainText` หรือแยก element ไม่ยัดหลายอย่างใน `role="status"` |
| `/api/browser/pair` ได้ 401 | ใช้ code ผิด/หมดอายุ (120 วินาที) → ขอ code ใหม่ทุกเทส |
| `/api/browser/pair` ได้ 422 | `agent_token` สั้นกว่า 43 หรือมีอักขระนอก `[A-Za-z0-9_-]` |
| `/api/browser/work` ได้ `EXTENSION_VERSION_MISMATCH` | ส่งเวอร์ชันไม่ตรง → ใช้ค่าจาก `GET /api/browser` ห้าม hardcode |
| ได้ `BROWSER_CONNECTION_BUSY` | ใช้ `connection_id` คนละค่าใน 90 วินาที → ใช้ uuid เดียวตลอดเทส |
| ได้ `OPERATION_LEASE_EXPIRED` | ใช้ `lease_epoch`/`connection_id` ไม่ตรง task ล่าสุด → sync ใหม่แล้วใช้ค่าจาก task นั้น |
| ได้ `STORY_RESULT_INVALID` | result ต้องเป็น `'[SIMULATION ONLY]\n' + task.topic` ตรงตัว |
| เทสผ่านบ้างล้มบ้าง | ห้ามเพิ่ม `waitForTimeout`; ใช้ `await expect(locator).toContainText(..., { timeout: 10000 })` |

## API ตอนกดเริ่มงาน (แสดงใน UI ด้วย)

| Code | ความหมาย | UI ต้องทำ |
|---|---|---|
| `DRAFT_NOT_SAVED` (ฝั่ง UI) | flush ไม่สำเร็จ | บอกให้รอสถานะ "บันทึกแล้ว" แล้วกดใหม่ ไม่เรียก API |
| `DRAFT_REVISION_CONFLICT` | แบบร่างเปลี่ยนหลังอ่าน revision | flush แล้วสร้าง key ใหม่ กดใหม่; ถ้ายังชน แนะนำโหลดแบบร่างล่าสุด |
| `STORY_DRAFT_INVALID` | ช่องบังคับไม่ครบ/ค่าไม่ถูก | แสดง issues จาก server และปิดปุ่ม |
| `STORY_CAPABILITY_UNAVAILABLE` | ไม่ใช่โหมดคลิปเดียว | บอกว่ารอบนี้รองรับคลิปเดียวเท่านั้น |
| `IDEMPOTENCY_CONFLICT` | key เดิมแต่ body ต่าง | สร้าง key ใหม่เมื่อ revision เปลี่ยน (T1 ข้อ 3) |
| `DRAFT_ASSET_MISSING`/`DRAFT_ASSET_INVALID` | ไฟล์แนบหาย/ไม่ตรง | ให้เลือกไฟล์ใหม่ |
| `PERMISSION_DENIED` | ไม่มี `jobs:create` | ซ่อนปุ่ม ไม่ logout |
| `HTTP_5xx`/`INTERNAL_ERROR` | server ล้ม | ให้กดลองใหม่ด้วย key เดิม แสดง trace ID |

## Desktop และ real Chrome

| อาการ | ทำอย่างไร |
|---|---|
| hook บล็อก `RUN_DEV.vbs`: "uncommitted migration" | มี migration ที่ยังไม่ commit → **หยุด** (กติกาห้ามมี migration) รายงาน |
| `CloseMainWindow()` แล้วหน้าต่างไม่ปิดใน 20 วินาที | close guard รอบันทึกแบบร่าง/มี save error → รออีก 20 วินาที; ยังไม่ปิด → **ห้าม Stop-Process** รายงาน |
| เปิดใหม่ 40 วินาทีไม่มีหน้าต่าง | ดู `.smartflow/logs/runtime.jsonl` หา `desktop.start_failed` แล้วรายงาน |
| topbar "ตัวประมวลผลกำลังเริ่ม" นานเกิน 30 วินาที | ดู `.smartflow/worker.heartbeat` และ `logs/worker.jsonl`; รายงาน |
| งานค้าง waiting + `EXTENSION_DISCONNECTED` > 120 วินาที | ตรวจอ่านอย่างเดียว: `browser_sessions.last_seen` ล่าสุด, `browser_pairings.state`; ห้ามแก้ registry/Extension → รายงานพร้อมค่าที่เห็น |
| งานเป็น `needs_review` + `SEND_ACCEPTANCE_UNKNOWN` | ห้าม resume; รายงาน (เป็นกลไกกันส่งซ้ำ ไม่ใช่บั๊ก) |
| `EXTENSION_VERSION_MISMATCH` ใน log จริง | helper/Extension ไม่ตรง 0.2.0 → รายงาน ห้าม build/ลงทะเบียนเอง |
