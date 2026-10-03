# P4 runbook: exact commands

ใช้คู่กับ [P4 execution plan](p4-integration.md) คำสั่งทั้งหมดรันที่ `C:\Users\RaywatSupaka\Desktop\project`
คำสั่ง bash ใช้ Git Bash; คำสั่งที่ขึ้นต้นด้วย `PS>` ใช้ PowerShell ถ้าคำสั่งยาวหรือมีเครื่องหมายคำพูดซ้อน ให้เขียนสคริปต์ลงไฟล์แล้วรัน

## เริ่มงาน

```bash
git status --short          # ต้องว่าง ถ้าไม่ว่าง หยุดและรายงาน
git log --oneline -3        # จดเลข commit ตั้งต้นลงรายงาน
.venv/Scripts/python.exe tools/check.py --scope ui typecheck   # baseline ต้องผ่านก่อนแก้
```

## ตรวจระหว่างทาง (เลือกตามไฟล์ที่แก้)

| แก้อะไร | คำสั่ง |
|---|---|
| ไฟล์ใน `frontend/src` | `.venv/Scripts/python.exe tools/check.py --scope ui typecheck` |
| เทสหนึ่งเคสใน Vitest | `.venv/Scripts/python.exe tools/check.py --scope ui --match "<ชื่อเคส>"` |
| `backend/smartflow/runtime.py` หรือ `tests/unit` | `.venv/Scripts/python.exe tools/check.py --scope unit runtime` |
| Python ทุกครั้ง | `.venv/Scripts/python.exe -m ruff check backend tests tools` และ `ruff format <ไฟล์ที่แก้>` |
| ไม่แน่ใจว่าต้องรันอะไร | `.venv/Scripts/python.exe tools/check.py --changed --dry-run` แล้วรันตาม scopes ที่ได้ |
| E2E หลังแก้ `frontend/src` (build ใหม่ + E2E ทุกเคส) | `.venv/Scripts/python.exe tools/check.py --scope build-ui e2e` |
| E2E หลังแก้เฉพาะไฟล์ใน `frontend/e2e` (ไม่ต้อง build) | `.venv/Scripts/python.exe tools/check.py --scope e2e --match "<ชื่อเคส>"` |
| E2E เคสเดียว | `.venv/Scripts/python.exe tools/check.py --scope e2e --match "story job"` |

## รันซ้ำเท่าที่จำเป็น (สำคัญ)

- แก้ error เล็ก ๆ แล้ว: รัน**เฉพาะเคสที่ล้ม**ด้วย `--match` ก่อน ผ่านแล้วจึงรัน scope ของไฟล์ที่แก้ ไม่รันทั้งระบบ
- ไม่ต้องเปิด server เอง: pytest/Vitest ไม่ใช้ server และ Playwright เปิด server ทดสอบให้เอง (port 8788) แล้วปิดเองทุกครั้ง
- `--scope all` รัน**ครั้งเดียว**ตอนปิดงาน; ถ้าล้ม แก้แล้วรันซ้ำเฉพาะ scope/เคสที่ล้ม ไม่เริ่ม all ใหม่ทั้งหมด
  ยกเว้นการแก้นั้นกระทบหลายระบบ (เช่น แก้ API contract) ให้รัน scope ที่ `--changed --dry-run` เลือกให้
- แก้แค่เอกสาร: ไม่รันเทส runtime เลย ตรวจลิงก์และ `git diff --check` อย่างเดียว
- build UI เฉพาะเมื่อแก้ `frontend/src` และต้องรัน E2E หรือปิดเปิด desktop; build ซ้ำโดยไม่มีการแก้ไม่จำเป็น

ทุกคำสั่ง check.py พิมพ์ `{"scope": ..., "seconds": ..., "exit_code": ...}` ให้จด seconds ลง commit message
exit_code ไม่เป็น 0 = ไม่ผ่าน ไปดู [troubleshooting](p4-troubleshooting.md)

## E2E story job

ไฟล์ `frontend/e2e/story-job.spec.ts` ใช้ server ทดสอบที่ Playwright เปิดเอง (port 8788, ข้อมูลชั่วคราว) ไม่กระทบ Chrome จริง
Token owner: `e2e-fixture-session-not-a-real-secret` (ดู `frontend/playwright.config.ts`) ทำตามลำดับ:

1. `request.post('/api/story-drafts', { headers: {Authorization, 'Idempotency-Key': uuid}, data: { config: { topic: 'e2e story job' } } })`
2. `page.goto('/#token=<owner token>')` → คลิกปุ่ม `เรื่องเล่า Shorts` → ไปขั้นสุดท้าย → กด `เริ่มงานจำลอง`
3. คาดหวังข้อความ "รอ Extension" (waiting + EXTENSION_DISCONNECTED) ภายใน 10 วินาที
4. จำลอง agent ผ่าน API (ไม่มี Chrome):
   - `GET /api/browser` (owner) → อ่าน `extension_id`, `extension_version`, `helper_version`
   - `POST /api/browser/pairings` body `{ extension_id }` → ได้ `{ id, code }`
   - `POST /api/browser/pair` header `Authorization: Bearer <code>` body
     `{ extension_id, agent_token, extension_version, helper_version }`; `agent_token` = สตริง `[A-Za-z0-9_-]` ยาว 43–100 ตัว
   - `POST /api/browser/work` header `Bearer <agent_token>` body
     `{ action:'sync', connection_id:<uuid คงที่>, extension_version, helper_version, capability:'story_simulator_v1' }` → `task`
   - `{ action:'grant', connection_id, operation_id, request_id, lease_epoch }` จาก task → `granted: true`
   - `{ action:'result', ...เหมือน grant, result: '[SIMULATION ONLY]\n' + task.topic }` → `persisted: true`
5. คาดหวัง UI แสดง "เสร็จ (จำลอง)" และป้าย `SIMULATION` ภายใน 10 วินาที; ตรวจว่า grant ครั้งที่สองได้ `granted: false`
6. ระหว่างเขียนเทสรัน `--scope e2e --match "story job"` (build-ui เฉพาะเมื่อแก้ `frontend/src` หลัง build ครั้งล่าสุด)
   เมื่อเคสใหม่ผ่านแล้ว รัน `--scope e2e` หนึ่งครั้ง ต้องผ่านครบ 12 เคส (11 เดิม + ใหม่)

## ปิดเปิด desktop หลังแก้ UI (ทำครั้งเดียวตอนท้าย)

```bash
.venv/Scripts/python.exe tools/check.py --scope build-ui
git status --short -- backend/smartflow/migrations/versions   # ต้องว่าง
```
```
PS> $w = Get-Process pythonw -EA SilentlyContinue | ? { $_.MainWindowTitle -eq 'SmartFlow Next' }; $w.Id
PS> [void]$w.CloseMainWindow()      # ปิดแบบปกติ ห้าม Stop-Process
PS> Start-Sleep 20; Get-Process -Id $w.Id -EA SilentlyContinue   # ต้องไม่มีผล = ปิดแล้ว
PS> wscript.exe .\RUN_DEV.vbs
PS> Start-Sleep 15; Get-Process pythonw | ? { $_.MainWindowTitle -eq 'SmartFlow Next' }   # ต้องเจอหน้าต่างใหม่
```
```bash
curl -s http://127.0.0.1:8766/ | grep -o 'assets/index-[^"]*\.js'   # ต้องตรงกับไฟล์ใน frontend/dist/assets
```

## Real Chrome end-to-end (ทำหลังเปิด desktop ใหม่)

1. ในหน้าต่าง SmartFlow Next เปิด `เรื่องเล่า Shorts` กรอกหัวข้อ "ทดสอบ P4" ไปขั้นสุดท้าย กด `เริ่มงานจำลอง`
   (ถ้า agent ควบคุมหน้าต่าง desktop ไม่ได้ ให้ข้ามขั้นนี้และเขียนในรายงานว่า "รอเจ้าของกดเอง")
2. Extension ใน Chrome จะรับงานเองภายใน 30–60 วินาที ห้ามแตะ Chrome
3. ตรวจแบบอ่านอย่างเดียว:
```bash
.venv/Scripts/python.exe -c "import sqlite3;c=sqlite3.connect('file:.smartflow/smartflow.db?mode=ro',uri=True);print(c.execute(\"select j.status,j.error_code,r.state from jobs j join story_operations o on o.job_id=j.id join operation_receipts r on r.operation_id=o.id order by j.created_at desc limit 1\").fetchone());print(c.execute(\"select count(*) from events where name='story.dispatch_marked'\").fetchone())"
```
   ผ่านเมื่อได้ `('completed', None, 'completed')` และจำนวน dispatch_marked ของงานนี้เป็น 1

## ปิดงาน

```bash
.venv/Scripts/python.exe tools/check.py --scope all   # ครั้งเดียวตอนจบ; ล้มแล้วแก้ ให้รันเฉพาะส่วนที่ล้มซ้ำ
git diff --check
git add <ไฟล์ที่แก้ทีละไฟล์>   # ห้าม git add -A
git commit -m "<type>: <สรุป>" -m "Checks: <คำสั่ง> <ผล> (<วินาที> s)"
```
`verification-p4.md` ต้องมี: commit ตั้งต้น/สุดท้าย, ตารางคำสั่ง+ผล+เวลา, ผล desktop, ผล real Chrome (หรือเหตุที่ไม่ได้ทำ),
สิ่งที่ยังไม่ทำ; เพิ่มแถวใน `docs/index.md` แล้วตรวจลิงก์ว่ามีไฟล์จริง
