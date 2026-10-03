# F5a runbook: exact commands

ใช้คู่กับ [F5a plan](f5-packaging.md) รันที่ `C:\Users\RaywatSupaka\Desktop\project`
คำสั่ง bash ใช้ Git Bash; บรรทัดที่ขึ้นต้นด้วย `PS>` ใช้ PowerShell; คำสั่งยาว/quote ซ้อน ให้เขียนสคริปต์ลงไฟล์ temp แล้วรัน
หลักรันซ้ำ: แก้นิดเดียวรันเฉพาะส่วนที่ล้ม; **build ชุดจริงเฉพาะเมื่อแก้ไฟล์ที่ไปอยู่ในชุด** (build.py, packaging/, backend, frontend, browser_extension)

## เริ่มงาน

```bash
git status --short                       # ต้องว่าง
git log --oneline -3                     # จด commit ตั้งต้น
cat "dist/SmartFlow Next/build-manifest.json"   # ต้องเป็น version 0.1.0, source_commit 5847f79...
```

## T0 เก็บชุดเก่า

```bash
mkdir -p build/previous-package
cp -r "dist/SmartFlow Next" "build/previous-package/SmartFlow Next 0.1.0"
cat "build/previous-package/SmartFlow Next 0.1.0/build-manifest.json"
ls "build/previous-package/SmartFlow Next 0.1.0/SmartFlow Next.exe"
```
ถ้า `dist/SmartFlow Next` ไม่มีอยู่แล้ว ให้เขียนในรายงานและข้าม T4

## ตรวจระหว่างทาง

| แก้อะไร | คำสั่ง |
|---|---|
| `backend/smartflow/__init__.py`, `pyproject.toml` | `.venv/Scripts/python.exe tools/check.py --scope unit api-core` |
| `frontend/src/App.tsx` | `.venv/Scripts/python.exe tools/check.py --scope ui typecheck` |
| `tools/build.py`, `packaging/*`, `tests/test_build_manifest.py` | `.venv/Scripts/python.exe tools/check.py --scope tooling` |
| `tools/packaged_smoke.py`, `tools/upgrade_smoke.py`, `tools/pairing_smoke.py` | `.venv/Scripts/python.exe -m ruff check tools` แล้วรัน smoke นั้นจริง |
| Python ทุกไฟล์ที่แก้ | `.venv/Scripts/python.exe -m ruff format <ไฟล์>` |

## Build ชุดจริง (หลัง commit เท่านั้น)

```bash
git status --short                                   # ต้องว่างก่อน build
time .venv/Scripts/python.exe tools/build.py         # ใช้เวลาหลายนาที; จดเวลา
cat "dist/SmartFlow Next/build-manifest.json"        # source_dirty ต้องเป็น false, version 0.2.0
ls "dist/SmartFlow Next/helper/SmartFlowNextHost.exe" "dist/SmartFlow Next/extension/chrome-mv3/manifest.json"
.venv/Scripts/python.exe -c "import hashlib,json;m=json.load(open('dist/SmartFlow Next/build-manifest.json'));print(hashlib.sha256(open('dist/SmartFlow Next/SmartFlow Next.exe','rb').read()).hexdigest()==m['exe_sha256'])"
```
build แล้ว `git status --short` ต้องยังว่าง (dist/ และ build/ อยู่ใน .gitignore) ถ้ามีไฟล์โผล่ ให้หาเหตุ อย่า commit binary

## Smoke ของชุด

```bash
time .venv/Scripts/python.exe tools/packaged_smoke.py          # ทุก key ใน report ต้อง true ยกเว้น clean_machine
cat build/packaged-smoke.json
time .venv/Scripts/python.exe tools/upgrade_smoke.py           # T4
cat build/upgrade-smoke.json
time .venv/Scripts/python.exe tools/pairing_smoke.py --story --helper "dist/SmartFlow Next/helper/SmartFlowNextHost"   # T5
```
smoke เปิด EXE กับ data dir และ port ของตัวเอง และปิดเองเมื่อจบ ไม่ต้องเปิด server เอง
หลัง pairing_smoke ตรวจว่าไม่เหลือ key ชั่วคราว:
```
PS> @(Get-ChildItem 'HKCU:\Software\Google\Chrome\NativeMessagingHosts' | ? { $_.PSChildName -like '*smoke_*' }).Count   # ต้องเป็น 0
```

## ตรวจว่า process ของ smoke ปิดหมด

```
PS> Get-CimInstance Win32_Process -Filter "Name='SmartFlow Next.exe' OR Name='SmartFlowNextHost.exe'" | Select ProcessId,CommandLine
```
ต้องไม่มี process ที่มาจาก `dist\` หรือ `build\previous-package\` ค้าง; ถ้ามี ดู [troubleshooting](f5-troubleshooting.md)

## ปิดงาน

```bash
.venv/Scripts/python.exe tools/check.py --scope all     # ครั้งเดียว; ล้มแล้วรันซ้ำเฉพาะส่วนที่ล้ม
git diff --check
git add <ไฟล์ทีละไฟล์>                                  # ห้าม git add -A; ห้าม add dist/ หรือ build/
git commit -m "<type>: <สรุป>" -m "Checks: <คำสั่ง> <ผล> (<วินาที> s)"
```
หลัง T1 (แก้ UI) ปิดเปิด Dev desktop หนึ่งครั้งตาม [P4 runbook](p4-runbook.md#ปิดเปิด-desktop-หลังแก้-ui-ทำครั้งเดียวตอนท้าย)
แล้วตรวจว่า topbar แสดง `v0.2.0` (ผ่าน `curl -s http://127.0.0.1:8766/` ว่าเสิร์ฟ bundle ใหม่)

`docs/delivery/verification-0.2.0.md` ต้องมี: commit ที่ build, ตาราง build/smoke/check พร้อมเวลา, เนื้อหา `build-manifest.json`
(ตัด path ส่วนตัวออก), ผล packaged/upgrade/pairing smoke แยกชั้น, สิ่งที่ยังไม่ได้ทำ (installer, signing, clean Windows, provider จริง)
