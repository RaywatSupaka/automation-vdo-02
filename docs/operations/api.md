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

## ข้อจำกัดปัจจุบัน

Input ใช้ Pydantic แต่ response models ยังไม่ได้ประกาศครบทุก route
Pagination/order/error contracts ที่เข้มขึ้นเป็นงาน F1 ใน [Foundation plan](../planning/foundation.md)
เปลี่ยน API แล้ว regenerate ด้วย `python tools/export_contract.py` และตรวจ diff เฉพาะ route ที่แก้

เทส: [test_api.py](../../tests/test_api.py) / scope `api`
