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
Setup ติดตั้ง dependencies ของ `browser_extension/` ด้วย; ยังไม่ลงทะเบียน native host หรือเปลี่ยน Chrome ของผู้ใช้
ใช้ Python bootstrap จึงไม่ต้องเปลี่ยน Windows PowerShell execution policy
เปิด Dev ด้วยการดับเบิลคลิก `RUN_DEV.vbs` เพื่อใช้ pythonw โดยไม่มี console
ตัวเปิดเลือก dev_bypass เมื่อไม่ระบุ SMARTFLOW_AUTH_MODE; ใช้ตัวตนจำลองแต่ยังตรวจ token/permission
การตั้ง role และ token อ่าน diagnostics อยู่ใน [Security](../operations/security.md)
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

## ปิดเปิดโปรแกรมหลังแก้ UX/UI ทุกครั้ง

เจ้าของโปรเจกต์อนุญาตให้รีสตาร์ตตามขั้นตอนนี้โดยไม่ต้องขอยืนยันซ้ำเมื่อทำได้อย่างปลอดภัย

1. ตรวจว่าเป็นหน้าต่างของโปรเจกต์ใหม่นี้ พร้อมระบุ entry point, โหมด และงาน/แบบร่างที่ค้างอยู่
2. Build frontend ที่แก้; ถ้าเปิด packaged EXE ต้อง build/update package นั้นก่อน
3. เก็บแบบร่างผ่านวิธีบันทึก/กู้คืนที่รองรับ และรอให้งานที่กำลังทำถึงจุดหยุดที่ปลอดภัย
4. ปิดหน้าต่างตามปกติ แล้วเปิดด้วย entry point และโหมดเดิม; Dev ใช้ `RUN_DEV.vbs` โดยไม่มี terminal
5. ตรวจหน้าต่างใหม่ว่าแสดง UX/UI ที่แก้แล้ว และคืนหน้าหรือแบบร่างเดิมเมื่อรองรับ
6. รายงานผลการเปิดใช้งานจริงแยกจากผล unit/browser test

ห้ามปิดโปรแกรมเก่า Chrome หรือ process อื่นแบบเหมารวม และห้าม force-kill งานเพื่อให้ผ่านขั้นตอนนี้
การกด F5, ดูหน้าเว็บ หรือดู screenshot จาก browser test ไม่แทนการปิดเปิด desktop
แบบร่าง Story ปัจจุบันยังอยู่ใน memory: ถ้ามีข้อมูลที่ยังเก็บคืนไม่ได้ ต้องแจ้งตัวบล็อกและการรีสตาร์ตที่ค้างให้ชัดเจน
ห้ามทิ้งข้อมูลเงียบ ๆ หรืออ้างว่าเปิดใช้แล้ว; ขอการตัดสินใจเฉพาะข้อมูลที่จำเป็นต้องทิ้งเมื่อไม่มีวิธีรักษาจริง
ข้อบังคับนี้ใช้เมื่อแก้ UX/UI; งานเอกสารอย่างเดียวไม่ต้อง build/restart

Source: [setup.py](../../tools/setup.py), [config.py](../../backend/smartflow/config.py),
[RUN_DEV.vbs](../../RUN_DEV.vbs), [RUN_DEV.bat](../../RUN_DEV.bat), [Vite config](../../frontend/vite.config.ts)
การตรวจ: [Testing](testing.md)
