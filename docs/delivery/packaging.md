# Windows packaging

## Build

```powershell
.venv\Scripts\python.exe tools/build.py
```

Script บิลด์ React/TypeScript แล้วใช้ PyInstaller รวม Python runtime, bytecode,
dependency DLLs และ frontend assets เป็นชุด portable โดยต้องใช้ working tree ที่ commit แล้ว
ถ้า `git status --porcelain` ไม่ว่าง script ปฏิเสธด้วย exit 2; `--allow-dirty` มีไว้ตรวจเฉพาะงานพัฒนา
ผลอยู่ `dist/SmartFlow Next/SmartFlow Next.exe`
ต้องส่งทั้งโฟลเดอร์พร้อม `_internal`, `helper/SmartFlowNextHost.exe` และ
`extension/chrome-mv3/`; EXE ไฟล์เดียวไม่ใช่ชุดที่สมบูรณ์
helper ใช้ [helper.spec](../../packaging/helper.spec) และ Extension ถูก build จาก source ที่ commit แล้ว
ชุดนี้ยังไม่ลงทะเบียน native host ในเครื่องลูกค้า

ไม่ส่ง source workspace, tests, node_modules, .venv, Git, เอกสารพัฒนา
หรืองาน/ข้อมูลจริงจากเครื่อง Dev ไปกับชุดของลูกค้า
DB, artifacts และ logs ถูกสร้างใน data directory ของลูกค้า ตาม [Setup](../development/setup.md)

`build-manifest.json` ระบุ app/helper/Extension version, source commit, dirty state, build time,
version ใน Extension manifest และ SHA-256 ของ EXE หลักกับ helper; build ปฏิเสธเมื่อเวอร์ชันไม่ตรงกัน
Binary และข้อมูล runtime ไม่เข้า Git

## ตรวจชุดที่บิลด์จริง

```powershell
.venv\Scripts\python.exe tools/packaged_smoke.py
.venv\Scripts\python.exe tools/upgrade_smoke.py
.venv\Scripts\python.exe tools/pairing_smoke.py --story --helper "dist/SmartFlow Next/helper"
```

Packaged smoke ใช้ EXE จริงกับ data dir และ port ชั่วคราวแยกโหมด prod/test ตรวจ frontend, API,
worker ready, การปฏิเสธ fault scenario ใน prod, draft restore, งาน Story `SIMULATION`,
การเปิดกลับมาพร้อม checkpoint, ไม่ส่งซ้ำ และ automatic save recovery
`SmartFlow Next.exe --desktop-smoke` เปิดหน้าต่างทดสอบของตัวเอง
ตรวจ React และการเชื่อม worker ผ่าน WebView2 แล้วเขียน marker และปิดหน้าต่างนั้น
Upgrade smoke ใช้ EXE 0.1.0 ที่เก็บไว้สร้าง DB schema 0001 แล้วเปิดด้วย 0.2.0 บน data dir เดิม
เพื่อตรวจ schema 0004, backup integrity และงานเก่าที่ยังอ่านได้
Pairing smoke ใช้ helper จากชุดผ่าน Chromium profile และ native host key ชั่วคราวของเทส

ผลนี้แยกจาก clean Windows, installer, installed Extension และ provider output จริง
ผลชุดปัจจุบันอยู่ใน [Verification 0.2.0](verification-0.2.0.md);
หลักฐานชุดเก่าอยู่ใน [Verification 0.1.0](verification-0.1.0.md)

## ก่อนแจกใช้งานจริง

ต้องมี installer, dependency detection (รวม WebView2), signing policy, clean-machine check,
restore UX ที่รักษาข้อมูล และ provider จริงที่ผ่านการตรวจ
ปัจจุบันยังเป็น portable foundation ตาม [Status](status.md)

Source: [build.py](../../tools/build.py), [smartflow.spec](../../packaging/smartflow.spec),
[helper.spec](../../packaging/helper.spec), [packaged_smoke.py](../../tools/packaged_smoke.py),
[upgrade_smoke.py](../../tools/upgrade_smoke.py), [pairing_smoke.py](../../tools/pairing_smoke.py)
