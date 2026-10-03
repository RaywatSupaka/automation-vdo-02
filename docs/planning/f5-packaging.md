# F5a portable package refresh: execution plan

แผนนี้เขียนให้ AI agent ทำต่อเองโดยไม่มีเจ้าของเฝ้าจอ เริ่มจาก `origin/dev` commit `8c523a3` หรือใหม่กว่า
อ่านตามลำดับ: [AGENTS.md](../../AGENTS.md) → [Standard workflow](../development/workflow.md) → ไฟล์นี้
→ [คู่มือคำสั่ง F5](f5-runbook.md) → [เมื่อเจอ error](f5-troubleshooting.md)
F5 เต็มรูปแบบ (installer, signing, clean Windows) ต้องให้เจ้าของตัดสินใจก่อน รอบนี้ทำเฉพาะ **F5a: ชุด portable ที่ทันสมัยและพิสูจน์ได้**

## สถานะตั้งต้น (ตรวจแล้ว 2026-10-03)

- `dist/SmartFlow Next/` เป็น EXE 0.1.0 จาก commit `5847f79` (ก่อน auth, drafts, P3, F2) ใช้เป็นต้นทางทดสอบอัปเกรดได้
- [build.py](../../tools/build.py) build frontend + [smartflow.spec](../../packaging/smartflow.spec) และเขียน `build-manifest.json`
  แต่ **ไม่มี helper และ Extension** ในชุด; helper build ด้วยคำสั่งครั้งเดียวและ spec อยู่ใน `build/` ที่ไม่เข้า Git
- [packaged_smoke.py](../../tools/packaged_smoke.py) ตรวจแค่ jobs/simulator/WebView และ **ใช้ scenario `unknown_send`/`save_failure`
  ในโหมด prod ซึ่ง B1 ปฏิเสธแล้ว (`SCENARIO_NOT_ALLOWED`)** ถ้ารันตอนนี้จะล้ม ต้องแก้ใน T3
- `__version__` = `0.1.0` ใน [`__init__.py`](../../backend/smartflow/__init__.py) ขณะที่ Extension/helper เป็น 0.2.0
- Helper อ่านเวอร์ชันจากค่าในโค้ด ไม่ต้องรวม `bridge_config.json` ใน helper; ชุดหลักรวมแล้วใน `smartflow.spec`

## กติกาเฉพาะรอบนี้ (เพิ่มจาก AGENTS.md)

1. ห้าม push; commit แยกตามงาน; `git add` ทีละไฟล์
2. ห้ามเพิ่ม migration, ห้ามติดตั้ง package/เครื่องมือใหม่ (รวม installer tools), ห้ามแก้ Extension source
3. Registry: อนุญาตเฉพาะ key ชั่วคราวที่ `tools/pairing_smoke.py` สร้างและลบเอง ห้ามลงทะเบียน helper ในชุดเข้ากับ
   `com.smartflow.next.dev` และห้ามแตะ host อื่น
4. ห้ามรัน EXE ใหม่หรือเก่ากับ `.smartflow/` (ข้อมูล Dev จริง) ทุกการรันต้องมี `SMARTFLOW_DATA_DIR` ชั่วคราว
5. ห้ามลบ `build/previous-package/` ที่สร้างใน T0; `dist/` เขียนทับได้หลัง T0 เท่านั้น
6. Build ชุดจาก working tree ที่ commit แล้วเท่านั้น (`source_dirty` ต้องเป็น false ในชุดที่รายงาน)
7. T1 แก้ UI จึงต้องปิดเปิด Dev desktop หนึ่งครั้งตาม [P4 runbook](p4-runbook.md#ปิดเปิด-desktop-หลังแก้-ui-ทำครั้งเดียวตอนท้าย)
   (CloseMainWindow เท่านั้น ห้าม Stop-Process) นอกจากนั้นห้ามปิดโปรแกรม Dev ที่เจ้าของเปิดอยู่

## งาน (ตามลำดับ; จบหนึ่งข้อ = ตรวจผ่าน + commit ยกเว้น T0)

**T0 เก็บชุดเก่าไว้ทดสอบอัปเกรด** (ไม่มี commit)
- คัดลอก `dist/SmartFlow Next` ไป `build/previous-package/SmartFlow Next 0.1.0` ตาม runbook แล้วตรวจ manifest ว่าเป็น `5847f79`

**T1 เวอร์ชัน 0.2.0** — `backend/smartflow/__init__.py`, `pyproject.toml` (field version), `frontend/src/App.tsx`
- เปลี่ยนเป็น `0.2.0`; ใน App.tsx fallback `'0.1.0'` ให้แสดง `'—'` แทนเมื่อยังไม่มี health
- ตรวจ `grep -rn "0\.1\.0" backend frontend/src tests tools` ไม่เหลือที่หมายถึงเวอร์ชันแอป
- ตรวจ `--scope unit api-core ui typecheck`; commit `chore: bump desktop app to 0.2.0`

**T2 รวม helper และ Extension ในชุด** — ไฟล์ใหม่ `packaging/helper.spec`, แก้ `tools/build.py`
1. `packaging/helper.spec`: เหมือน `build/SmartFlowNextHost.spec` แต่ใช้ `root = Path(SPECPATH).parent`,
   script `root/"native_entry.py"`, `pathex=[str(root/"backend")]`, `name="SmartFlowNextHost"`, `console=True`, `upx=False`
2. `build.py` หลัง build ชุดหลัก: รัน PyInstaller กับ `packaging/helper.spec` ด้วย `--distpath build/helper-dist --workpath build/helper-work`
   แล้วคัดลอก `build/helper-dist/SmartFlowNextHost` → `dist/SmartFlow Next/helper/` (ต้องทำหลังชุดหลัก เพราะ PyInstaller ล้างโฟลเดอร์ชุดหลัก)
3. Build Extension ด้วย `npm run build` ใน `browser_extension/` (env จาก `node_environment()`) แล้วคัดลอก
   `browser_extension/.output/chrome-mv3` → `dist/SmartFlow Next/extension/chrome-mv3/`
4. ปฏิเสธการ build เมื่อ `git status --porcelain` ไม่ว่าง (exit 2 พร้อมข้อความ) เว้นแต่ใส่ `--allow-dirty`
5. แยกการสร้าง manifest เป็นฟังก์ชัน pure `build_manifest(target, commit, dirty, now)` ที่เพิ่ม `app_version`,
   `helper_version`/`extension_version` (จาก `bridge_config.json`), `helper_sha256`, `extension_manifest_version`
   (อ่านจาก `extension/chrome-mv3/manifest.json`) และ SHA-256 ของ EXE ทั้งสอง
6. เทสใหม่ `tests/test_build_manifest.py` (สร้างโฟลเดอร์ปลอมใน tmp_path ไม่รัน PyInstaller): manifest ครบทุก field,
   hash ตรงไฟล์, เวอร์ชันไม่ตรงกันต้อง raise; เทสการปฏิเสธ dirty ด้วย fake git output
7. เพิ่ม mapping ใน `tools/check_selection.py`: `tools/build.py` และ `tests/test_build_manifest.py` → `tooling`; `packaging/*` → `tooling`
8. ตรวจ `--scope tooling` แล้ว build จริงหนึ่งครั้งตาม runbook; commit `feat: bundle native helper and Extension in the portable package`

**T3 Packaged smoke ครอบงานปัจจุบัน** — `tools/packaged_smoke.py`
- แยกเป็นสองช่วง: **ช่วง prod** (`SMARTFLOW_MODE=prod`) และ **ช่วง test** (`SMARTFLOW_MODE=test`) คนละ data dir
- ช่วง prod ตรวจ: health `version == "0.2.0"` และ `worker_state == "ready"`; หน้า UI; job `success` เสร็จ;
  `unknown_send` ถูกปฏิเสธด้วย `SCENARIO_NOT_ALLOWED`; draft POST→PATCH→ปิด EXE→เปิดใหม่→GET ได้ค่าเดิม;
  งาน Story: POST `/api/stories` → จำลอง agent ผ่าน API แบบเดียวกับ E2E ([P4 runbook](p4-runbook.md#e2e-story-job))
  → completed, ไฟล์ใน `<data>/story-artifacts/` SHA-256 ตรง receipt, diagnostics ไม่มีหัวข้อเรื่อง
- ช่วง test: ย้ายเคสเดิม `unknown_send` restart-no-resend และ `save_failure` มาไว้ที่นี่ (ผลต้องเหมือนเดิม)
- ช่วง desktop: `desktop --desktop-smoke` เหมือนเดิม
- report เพิ่ม key: `version`, `worker_ready`, `prod_fault_scenarios_denied`, `draft_restore`, `story_simulation`
- ใช้ `wait_for` ที่มีอยู่ (มี deadline) ห้ามเพิ่ม sleep ยาว; commit `test: extend packaged smoke to drafts and Story simulation`

**T4 พิสูจน์อัปเกรดจาก 0.1.0** — ไฟล์ใหม่ `tools/upgrade_smoke.py`
- ใช้ EXE เก่าจาก T0 รัน `serve` กับ data dir ชั่วคราว สร้างงาน `success` 1 งาน (ถ้า API เก่ารับ) แล้วปิด
- ใช้ EXE ใหม่รัน `serve` กับ data dir เดิม: ต้องได้ schema `0004`, มี `backups/before-0001-*.sqlite3`
  ที่ `PRAGMA integrity_check` = ok, งานเก่ายังอ่านได้, health ready
- เขียนผลเป็น JSON ที่ `build/upgrade-smoke.json`; commit `test: prove portable upgrade from 0.1.0 data`

**T5 ตรวจ helper ในชุดกับ Chrome แบบแยก** — `tools/pairing_smoke.py`
- เพิ่ม `--helper <โฟลเดอร์>` (ค่าเดิม `build/native/SmartFlowNextHost`) แล้วรัน `--story` กับ `dist/SmartFlow Next/helper`
- commit `test: run pairing smoke against the packaged helper`

**T6 เอกสาร** — [packaging.md](../delivery/packaging.md) (โครงชุดใหม่ helper/extension, manifest, smokes, upgrade),
[status](../delivery/status.md) header เป็น 0.2.0, [foundation](foundation.md) แถว F5 เป็น "บางส่วน (F5a)",
สร้าง `docs/delivery/verification-0.2.0.md` (ตามกติกา `verification-<version>.md`) และลิงก์ใน [index](../index.md)

ถ้าเวลาไม่พอ: T0 → T1 → T2 → T3 → T6 ก่อน; T4/T5 ข้ามได้แต่ต้องเขียนในรายงาน

## ไม่อยู่ในรอบนี้ (ต้องให้เจ้าของตัดสินใจ)

เครื่องมือ installer (MSIX/Inno Setup/WiX), ใบรับรอง code signing, VM/เครื่อง clean Windows, การตรวจ WebView2,
นโยบายข้อมูลตอนถอนติดตั้ง และการลงทะเบียน helper ของชุดในเครื่องลูกค้า

## หยุดและรายงานเมื่อ

- ต้องติดตั้งเครื่องมือ, แก้ registry นอก pairing_smoke, เพิ่ม migration หรือแก้ Extension source
- PyInstaller build ล้มซ้ำ 2 รอบหลังแก้, Windows Defender/antivirus กักไฟล์, พื้นที่ดิสก์ไม่พอ
- EXE เก่า 0.1.0 เปิดไม่ได้ (บันทึกอาการแล้วข้าม T4 ได้), เทสที่ไม่เกี่ยวล้ม, หรือพบไฟล์ที่คนอื่นแก้
