# F5a troubleshooting: เจอ error แล้วทำอะไร

ใช้คู่กับ [F5a plan](f5-packaging.md) และ [คู่มือคำสั่ง](f5-runbook.md)
หลักทั่วไปและรูปแบบรายงาน: [Standard workflow](../development/workflow.md#4-เมื่อเจอ-error) แก้ 2 รอบไม่ผ่าน → หยุดและรายงาน

## Build (PyInstaller / build.py)

| อาการ | สาเหตุที่พบบ่อย | ทำอย่างไร |
|---|---|---|
| `build.py` exit 2 "working tree is dirty" | ยังไม่ commit | commit งานก่อน แล้ว build ใหม่ ห้ามใช้ `--allow-dirty` กับชุดที่จะรายงาน |
| `PermissionError`/`Access is denied` ที่ `dist\SmartFlow Next` | EXE จากชุดนั้นยังเปิดอยู่ (smoke ค้าง) | หา process ตาม runbook; ถ้า CommandLine อยู่ใน `dist\` หรือ `build\` ของโปรเจกต์ ปิดได้ด้วย `Stop-Process -Id`; อย่างอื่นห้ามปิด → รายงาน |
| `npm`/`node` not found | ไม่ได้ใช้ env จาก `node_environment()` | เรียก npm ผ่าน env เดียวกับที่ build.py ใช้กับ frontend |
| PyInstaller `ModuleNotFoundError` ตอน build | path ใน spec ผิด | ตรวจ `pathex=[root/"backend"]` และ `root = Path(SPECPATH).parent` |
| EXE เปิดแล้ว `ModuleNotFoundError` ตอนรัน | import แบบ dynamic | เพิ่มชื่อ module ใน `hiddenimports` ของ spec นั้นแล้ว build ใหม่ |
| EXE ฟ้องหาไฟล์ json/migrations ไม่เจอ | data file ไม่อยู่ใน `datas` | เพิ่มใน `datas` ของ spec (ดูแบบใน `smartflow.spec`) |
| helper ไม่อยู่ใน `dist\SmartFlow Next\helper` | คัดลอกก่อน build ชุดหลัก | ชุดหลักต้อง build ก่อน แล้วค่อยคัดลอก helper/extension |
| `exe_sha256` ไม่ตรง | manifest เขียนก่อนคัดลอกเสร็จ/ไฟล์ถูกแก้ | สร้าง manifest เป็นขั้นสุดท้ายของ build.py |
| Defender/antivirus ลบหรือกัก EXE | false positive ของ PyInstaller | **หยุด** รายงาน ห้ามปิด antivirus หรือเพิ่ม exclusion เอง |
| ดิสก์เต็ม | build/ สะสม | ลบเฉพาะ `build/helper-work`, `build/native-work`, `build/smartflow` ได้; ห้ามลบ `build/previous-package` |

## Packaged smoke

| อาการ | ทำอย่างไร |
|---|---|
| ช่วง prod ได้ `SCENARIO_NOT_ALLOWED` จาก `unknown_send`/`save_failure` | ถูกต้องตาม B1: ย้ายเคสพวกนี้ไปช่วง test (`SMARTFLOW_MODE=test`) และในช่วง prod ให้ assert ว่าถูกปฏิเสธ |
| `Packaged smoke condition timed out` | ดู log ใน data dir ชั่วคราวของ smoke (`logs/runtime.jsonl`, `logs/worker.jsonl`) หา `code` แล้วเทียบกับ [errors.py](../../backend/smartflow/errors.py) |
| health ไม่มี `worker_state` หรือ version ไม่ใช่ 0.2.0 | EXE เป็น build เก่า | build ใหม่หลัง commit T1 |
| `worker_state` ค้าง `starting` | worker เขียน heartbeat ไม่ได้ | ตรวจ `<data>/worker.heartbeat` และ `logs/worker.jsonl`; data dir ต้องเขียนได้ |
| 401 จาก API ของ EXE | token env ไม่ตรง | ใช้ `SMARTFLOW_API_TOKEN` เดียวกับ header ใน client |
| Story ค้าง `waiting` + `EXTENSION_DISCONNECTED` | ยังไม่ได้จำลอง agent หรือ pairing ไม่สำเร็จ | ทำตามลำดับใน [P4 runbook](p4-runbook.md#e2e-story-job): pairings → pair (Bearer code) → work sync/grant/result |
| `EXTENSION_VERSION_MISMATCH` ตอน sync | ส่งเวอร์ชันเอง | อ่าน `extension_version`/`helper_version` จาก `GET /api/browser` |
| desktop smoke ไม่มี `desktop-smoke.json` | WebView2 ไม่พร้อมหรือหน้าต่างไม่ render | รันซ้ำหนึ่งครั้ง; ยังไม่ได้ → รายงานพร้อม log ใน data dir |
| process ค้างหลัง smoke | smoke ปิดไม่ครบ | ปิดเฉพาะ process ที่ CommandLine อยู่ใน `dist\`/`build\` ของโปรเจกต์ และแก้ `stop()` ใน smoke ให้รอจบ |
| path ภาษาไทยทำให้พัง | smoke ตั้งใจใช้ temp ที่มีภาษาไทยเพื่อทดสอบ | แก้โค้ดที่จัดการ path (ใช้ `Path`, ไม่ encode เอง) ห้ามเปลี่ยน prefix ภาษาไทยออก |

## Upgrade smoke (T4)

| อาการ | ทำอย่างไร |
|---|---|
| EXE 0.1.0 ไม่รับ env/คำสั่ง `serve` | บันทึก exit code และ log; ลองแค่เปิดให้สร้าง DB แล้วปิด; ยังไม่ได้ → ข้าม T4 และรายงาน |
| API ของ 0.1.0 ไม่มี auth แบบใหม่ | ไม่ต้องสร้างงาน ใช้ DB ว่างที่ schema 0001 เป็นต้นทาง |
| EXE ใหม่ฟ้อง unknown revision | DB ไม่ได้มาจาก 0.1.0 จริง | ตรวจ `alembic_version` ของ DB ต้นทางก่อนอัปเกรด |
| ไม่มีไฟล์ `backups/before-0001-*` | migrate ไม่ได้ทำ backup | **หยุด** รายงาน (เป็นข้อกำหนดของ migration safety) |
| integrity_check ไม่ใช่ ok | backup/DB เสีย | **หยุด** รายงานพร้อมชื่อไฟล์ ห้ามลบหรือซ่อม |

## Pairing smoke กับ helper ในชุด (T5)

| อาการ | ทำอย่างไร |
|---|---|
| Chrome ไม่เรียก helper | manifest ชั่วคราวชี้ path ผิด | ตรวจว่า `--helper` ชี้โฟลเดอร์ที่มี `SmartFlowNextHost.exe` และ smoke คัดลอกไป temp ถูก |
| เหลือ key `smoke_` ใน registry | smoke ล้มกลางทาง | ลบได้เฉพาะ key ที่ชื่อขึ้นต้น `com.smartflow.next.smoke_` ด้วย `Remove-Item` แล้วรายงาน; key อื่นห้ามแตะ |
| `Expected isolated credential` | ใช้ data dir ซ้ำ | ให้ smoke สร้าง temp ใหม่ทุกครั้ง |

## Dev desktop หลัง T1

ใช้ตาราง Desktop ใน [P4 troubleshooting](p4-troubleshooting.md#desktop-และ-real-chrome) (ปิดไม่ได้ → ห้าม Stop-Process, รายงาน)
