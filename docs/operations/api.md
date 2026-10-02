# API and CLI

Source: [api.py](../../backend/smartflow/api.py), [cli.py](../../backend/smartflow/cli.py),
[jobs.py](../../backend/smartflow/jobs.py)
สัญญาที่ generate แล้ว: [openapi.json](../../contracts/openapi.json)
ใช้ `rg` หา route ที่ต้องการก่อนอ่าน schema ทั้งไฟล์

## เปิด session สำหรับ AI / Dev

ตั้ง token เฉพาะ session ใน environment ห้ามเก็บใน Git, log หรือ command argument

```powershell
$env:SMARTFLOW_API_TOKEN = [guid]::NewGuid().ToString('N')
.venv\Scripts\python.exe -m smartflow.cli serve --port 8766
```

เรียกจาก process ที่ได้รับ token เดียวกันใน environment:

```powershell
.venv\Scripts\python.exe -m smartflow.cli doctor
.venv\Scripts\python.exe -m smartflow.cli api --path /api/jobs
.venv\Scripts\python.exe -m smartflow.cli api --method POST --path /api/jobs --key demo-command-01 --body examples/create-job.json
```

Payload ตัวอย่างอยู่ [examples/create-job.json](../../examples/create-job.json)
ตัวอย่างนี้สร้างงาน simulator; ไม่ได้ส่งไปยัง AI จริง

## Routes ตามหน้าที่

| หน้าที่ | Route |
|---|---|
| สถานะโปรแกรม | GET /api/health |
| สร้าง / ดูรายการงาน | POST /api/jobs, GET /api/jobs |
| งานเดียว / เหตุการณ์ | GET /api/jobs/{job_id}, GET /api/jobs/{job_id}/events |
| คำสั่งทำต่อ / ยกเลิก / ตรวจผลเดิม | POST /api/jobs/{job_id}/commands/{resume,cancel,reconcile} |
| วินิจฉัย / ส่งออก | GET /api/jobs/{job_id}/diagnostics, GET /api/jobs/{job_id}/support-bundle |
| โครงสร้าง / แถว DB | GET /api/diagnostics/database, GET /api/diagnostics/database/{table} |
| Log ล่าสุด | GET /api/diagnostics/logs |
| Error catalog / schema | GET /api/errors, GET /api/openapi.json |

ทุก route ใช้ Bearer token ตาม [Security](security.md)
POST /api/jobs ต้องมี Idempotency-Key; การ retry ต้องใช้ key เดิมกับ input เดิม
แต่ละ HTTP response มี X-Trace-ID สำหรับตาม request
Error envelope และการกู้คืนอยู่ใน [Errors](errors.md)

## Response, trace และ pagination

Input/output ใช้ Pydantic; ดู [contracts.py](../../backend/smartflow/contracts.py) และ OpenAPI
ทุก JSON route มี success schema และ error envelope; support-bundle สำเร็จเป็น ZIP binary
`GET /api/errors` เป็น catalog ของ error code/recovery ที่ใช้จริง
Job `trace_id` คงเดิมตลอดอายุงาน; X-Trace-ID เปลี่ยนทุก HTTP request รวม retry
คำสั่ง resume/cancel/reconcile บันทึก `details.command_trace_id` ใน event แม้เป็น no-op
คำสั่งที่ถูกปฏิเสธไม่แก้ DB; ตาม `job.command` และ `api.request` ใน log ด้วย command trace
Create ที่ใช้ key ซ้ำได้ job trace เดิม; `job.create` log เชื่อมกับ request trace ใหม่

| รายการ | Pagination / order |
|---|---|
| jobs | limit 1–200 (default 100), offset >= 0; created_at DESC, id DESC |
| job events | limit 1–500 (default 200), after >= 0; id ASC, ไม่รวม after |
| DB projections | limit 1–200 (default 50), offset >= 0; jobs ตามข้างบน, receipts updated_at DESC/job_id DESC, events id DESC |
| logs | limit 1–200 (default 50); ล่าสุดจากไฟล์ปัจจุบันของ API/worker เรียง at ASC |

Array ว่างหมายถึงไม่มีข้อมูลในหน้านั้น; offset pagination ไม่ใช่ snapshot เมื่อมีการเพิ่ม/เปลี่ยนงาน
ใช้ event ID สุดท้ายเป็น after เพื่ออ่าน event ต่อเนื่องโดยไม่ซ้ำ
HTTP ไม่ retry คำสั่งให้เอง; create retry ใช้ key+input เดิมเสมอ
Resume/cancel ซ้ำอาจเป็น no-op ตามสถานะ; reconcile อ่านผลเดิมเท่านั้นและอาจคืน 409 เมื่อสถานะเปลี่ยนแล้ว
การ resume ไม่อนุญาตส่งใหม่เมื่อ receipt ยัง dispatching/unknown; ดู [Automation](../architecture/automation.md)

เปลี่ยน API แล้ว regenerate ด้วย `python tools/export_contract.py` และตรวจ diff เฉพาะ route ที่แก้

เทส: [test_api.py](../../tests/test_api.py) / scope `api`
