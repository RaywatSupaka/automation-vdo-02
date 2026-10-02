# Windows packaging

## Build

```powershell
.venv\Scripts\python.exe tools/build.py
```

Script บิลด์ React/TypeScript แล้วใช้ PyInstaller รวม Python runtime, bytecode,
dependency DLLs และ frontend assets เป็นชุด portable
ผลอยู่ `dist/SmartFlow Next/SmartFlow Next.exe`
ต้องส่งทั้งโฟลเดอร์พร้อม `_internal`; EXE ไฟล์เดียวไม่ใช่ชุดที่สมบูรณ์

ไม่ส่ง source workspace, tests, node_modules, .venv, Git, เอกสารพัฒนา
หรืองาน/ข้อมูลจริงจากเครื่อง Dev ไปกับชุดของลูกค้า
DB, artifacts และ logs ถูกสร้างใน data directory ของลูกค้า ตาม [Setup](../development/setup.md)

`build-manifest.json` ระบุ version, source commit, dirty state, build time และ SHA-256 ของ EXE
Binary และข้อมูล runtime ไม่เข้า Git

## ตรวจชุดที่บิลด์จริง

```powershell
.venv\Scripts\python.exe tools/packaged_smoke.py
```

Smoke ใช้ EXE จริงกับ sandbox และ port ของตัวเอง ตรวจ frontend, API, worker,
การเปิดกลับมาพร้อม checkpoint, ไม่ส่งซ้ำ และ automatic save recovery
`SmartFlow Next.exe --desktop-smoke` เปิดหน้าต่างทดสอบของตัวเอง
ตรวจ React และการเชื่อม worker ผ่าน WebView2 แล้วเขียน marker และปิดหน้าต่างนั้น

ผลนี้แยกจาก clean Windows, installer, installed Extension และ provider output จริง
ผลที่ตรวจแล้วอยู่ใน [Verification 0.1.0](verification-0.1.0.md)

## ก่อนแจกใช้งานจริง

ต้องมี installer, dependency detection (รวม WebView2), signing policy, clean-machine check,
upgrade/backup/restore ที่รักษาข้อมูล และ provider จริงที่ผ่านการตรวจ
ปัจจุบันยังเป็น portable foundation ตาม [Status](status.md)

Source: [build.py](../../tools/build.py), [smartflow.spec](../../packaging/smartflow.spec),
[packaged_smoke.py](../../tools/packaged_smoke.py)
