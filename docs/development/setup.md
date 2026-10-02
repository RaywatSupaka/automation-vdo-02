# Development setup

ใช้ Windows x64, Python 3.11 และ Edge WebView2 Runtime สำหรับหน้าต่าง desktop

```powershell
cd C:\Users\RaywatSupaka\Desktop\project
.\SETUP.bat
wscript.exe .\RUN_DEV.vbs
```

Setup ดาวน์โหลด Node 24.21.0 ไป `.tools/` และตรวจ SHA-256 โดยไม่เปลี่ยน Node ของเครื่อง
ติดตั้ง Python dependencies ตาม constraints และ npm dependencies ตาม lockfile
พร้อมบิลด์ frontend และติดตั้ง Playwright Chromium สำหรับเทส
ใช้ Python bootstrap จึงไม่ต้องเปลี่ยน Windows PowerShell execution policy
เปิด Dev ด้วยการดับเบิลคลิก `RUN_DEV.vbs` เพื่อใช้ pythonw โดยไม่มี console
`RUN_DEV.bat` ยังใช้ได้และส่งต่อไปตัวเปิดเดียวกัน; อาจเห็น console แวบแรกจากตัว BAT
Log ยังเก็บในไฟล์และอ่านผ่าน API/หน้า “บันทึกระบบ” ได้ ไม่ต้องเปิด terminal ทิ้งไว้
ถ้า desktop เริ่มไม่ได้ จะบันทึก `desktop.start_failed` และแสดงข้อความให้ตรวจ offline doctor

## แหล่งข้อมูล

| โหมด | ตำแหน่งเริ่มต้น |
|---|---|
| Dev | `.smartflow/` ภายใต้ working directory |
| EXE / Prod | `%LOCALAPPDATA%/SmartFlowNext` |
| Test | temporary directory แยกต่อ fixture/run |

ตั้ง `SMARTFLOW_DATA_DIR` เพื่อแยก sandbox ได้ ห้ามชี้เทสไปยังข้อมูลงานจริง
`SMARTFLOW_MODE` รับ `dev`, `prod`, `test`; `SMARTFLOW_PORT` เริ่มที่ `8766`
UI, backend และ worker ทำงานในเครื่องเดียวกัน ไม่ต้องมีเซิร์ฟเวอร์กลาง

## แก้หน้าจอ

`npm run dev` ใน `frontend/` เปิด Vite บน loopback และ proxy `/api` ไป port 8766
เปิด backend และกำหนด session token ตาม [API and CLI](../operations/api.md)
หน้า Dev ที่ไม่ได้เปิดผ่าน desktop ให้กรอก token ของ backend session ที่ต้องการเชื่อมต่อ
ตัวเปิด Dev ใช้หน้าเว็บที่ build แล้ว; หลังแก้ UI ให้ `npm run build` เพื่อเปิดดูชุดใหม่ใน desktop

Source: [setup.py](../../tools/setup.py), [config.py](../../backend/smartflow/config.py),
[RUN_DEV.vbs](../../RUN_DEV.vbs), [RUN_DEV.bat](../../RUN_DEV.bat), [Vite config](../../frontend/vite.config.ts)
การตรวจ: [Testing](testing.md)
