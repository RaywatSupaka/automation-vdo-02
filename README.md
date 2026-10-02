# SmartFlow Next

โครงสร้างใหม่สำหรับโปรแกรม Windows ที่ AI พัฒนา ทดสอบ และวิเคราะห์ปัญหาผ่าน API ได้

**สถานะ 0.1.0: foundation ที่รันได้ ใช้ผู้ให้บริการจำลองเท่านั้น ยังไม่สร้างวิดีโอจริง**
เริ่มใหม่ทั้งหมด ไม่มีการนำเอกสาร โค้ด งาน หรือบัญชีจากโปรเจกต์เก่ามาใช้

## สิ่งที่ทำได้

- หน้าจอ React ภาษาไทย: สร้างงาน ดูคิว ดู error และ timeline ตรวจฐานข้อมูล และอ่าน log
- FastAPI พร้อม OpenAPI, session authentication, trace ID และรหัส error คงที่
- SQLite / SQLAlchemy / Alembic: งาน คำขอ checkpoint และเหตุการณ์ที่บันทึกใน transaction
- worker แยก process พร้อมกู้คืนเมื่อหยุด และ supervisor ที่จำกัดการเริ่มใหม่ 3 ครั้งต่อ session
- ป้องกันคำสั่งสร้างงานซ้ำด้วย Idempotency-Key และไม่ส่งซ้ำเมื่อยังยืนยันการรับไม่ได้
- จำลอง 6 กรณี: สำเร็จ, ต้อง login, ส่งไม่แน่ใจ, บันทึกไฟล์เสีย, ไม่พร้อมชั่วคราว, ผลลัพธ์ค้าง
- ส่งออก ZIP ข้อมูลวิเคราะห์ที่ไม่รวมเนื้อหาผู้ใช้ และตรวจ offline เมื่อ API เปิดไม่ได้
- บิลด์เป็น portable EXE directory โดยรวม Python และหน้าเว็บที่ build แล้ว

## เริ่มพัฒนา

ใช้ Windows x64, Python 3.11 และ Edge WebView2 Runtime สำหรับหน้าต่าง desktop
setup ดาวน์โหลด Node 24.21.0 มาไว้เฉพาะ `.tools/` พร้อมตรวจ SHA-256; ไม่เปลี่ยน Node ของเครื่อง

```powershell
cd C:\Users\RaywatSupaka\Desktop\project
powershell -File tools/setup.ps1
.\RUN_DEV.bat
```

`RUN_DEV.bat` เปิด desktop UI ใหม่และ worker โดยใช้ข้อมูลใน `.smartflow/`
EXE ใช้ `%LOCALAPPDATA%\SmartFlowNext` โดยปริยาย ข้อมูลแยกจากโฟลเดอร์ติดตั้ง
ตั้ง `SMARTFLOW_DATA_DIR` ได้เมื่อต้องการ sandbox สำหรับงานทดสอบ

## ให้ AI ใช้งานผ่าน API

ตั้ง token เฉพาะ session ใน environment ห้ามบันทึกลง Git หรือ log

```powershell
$env:SMARTFLOW_API_TOKEN = [guid]::NewGuid().ToString('N')
.venv\Scripts\python.exe -m smartflow.cli serve --port 8766
```

เรียกจาก process ที่ได้รับ token เดียวกันใน environment:

```powershell
.venv\Scripts\python.exe -m smartflow.cli doctor
.venv\Scripts\python.exe -m smartflow.cli api --path /api/jobs
.venv\Scripts\python.exe -m smartflow.cli api --method POST --path /api/jobs --key demo-command-01 --body examples/create-job.json
.venv\Scripts\python.exe -m smartflow.cli api --path /api/diagnostics/database/jobs
.venv\Scripts\python.exe -m smartflow.cli api --path /api/diagnostics/logs
```

ตรวจข้อมูลในเครื่องโดยไม่ต้องมี API/token และไม่สร้าง DB ใหม่:

```powershell
.venv\Scripts\python.exe -m smartflow.cli doctor --offline
```

อ่าน [contracts/openapi.json](contracts/openapi.json) สำหรับสัญญา API ที่สร้างจาก source
หรือ GET `/api/openapi.json` ด้วย Bearer token ของ session ที่เปิดอยู่

## ทดสอบและบิลด์

```powershell
.venv\Scripts\python.exe tools/check.py --scope workflow
.venv\Scripts\python.exe tools/check.py --scope api
powershell -File tools/build.ps1
```

ผลบิลด์: `dist/SmartFlow Next/SmartFlow Next.exe` ต้องเก็บไฟล์ทั้งโฟลเดอร์ไว้ด้วยกัน
นี่คือ portable foundation; ยังไม่ใช่ installer พร้อมแจกบนเครื่องลูกค้า
ต้องตรวจ WebView2, code signing/installer, clean Windows และ provider จริงก่อนส่งมอบใช้งานผลิตสื่อ

อ่าน [ARCHITECTURE.md](ARCHITECTURE.md), [TESTING.md](TESTING.md) และ [RELEASE.md](RELEASE.md) ตามงาน
