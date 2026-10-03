# Focused test selection

เป้าหมาย: แก้หนึ่ง feature แล้วตรวจเฉพาะพฤติกรรมและสัญญาที่ได้รับผล ไม่รันทั้งระบบทุกครั้ง
ชื่อ scopes และตัวอย่างพื้นฐานอยู่ใน [Testing](testing.md)

## รอบพัฒนาในเครื่อง

1. เริ่ม scope เล็ก เช่น unit-auth หรือ unit-input; ใช้ --match เลือกชื่อเคสได้
2. เปลี่ยน boundary จึงเพิ่ม integration ของส่วนนั้น เช่น auth หรือ api-core
3. เพิ่ม E2E เมื่อเปลี่ยน UI/API interaction; เปิด desktop smoke เมื่อเปลี่ยนตัวเปิด/native integration
4. ไม่บิลด์ EXE ยกเว้นงาน packaging/ส่งมอบ หรือจำเป็นต้องพิสูจน์ packaged behavior
5. หากเคสล้มเหลว รันเฉพาะเคสนั้นกับสัญญาที่กระทบหลังแก้ ไม่เริ่มชุดเดิมทั้งหมดโดยอัตโนมัติ

`--match` ใช้ pytest -k, Vitest -t หรือ Playwright --grep ตาม scope
ตัวอย่าง `--scope e2e --match support` เลือกเฉพาะ UI ของ support
หากไม่มีเคสตรงชื่อ ให้ถือว่าไม่ผ่าน/ไม่มีหลักฐาน ห้ามใช้ตัวเลือก pass-with-no-tests
ต้องการ test ID ตรงตัวใช้ `python -m pytest tests/test_auth.py::test_missing_policy_fails_closed_before_handler`

## เลือกตามไฟล์

- `--changed` รวม staged/unstaged และ untracked ที่ Git ไม่ ignore
- `--changed --base <commit>` เปรียบเทียบ baseline กับ working tree (CI เป็น checkout สะอาด)
- `--dry-run` แสดง scope/คำสั่งโดยไม่รันทดสอบ; `--plan-json <path>` บันทึกแผน
- Rename ตรวจทั้ง path เก่าและใหม่; ไฟล์ไม่อยู่ใน mapping เลือก all เพื่อไม่ตกหล่น
- Mapping เป็นระดับไฟล์ ไม่ได้วิเคราะห์ call graph; ผู้แก้ต้องเพิ่ม scopes เมื่อทราบผลกระทบเพิ่มเติม
- แหล่ง mapping เดียว: [check_selection.py](../../tools/check_selection.py); เพิ่ม mapping พร้อม feature ใหม่
- หลาย Python scopes รวมใน pytest process เดียว; parent directory ครอบ child แล้วไม่ collect ซ้ำ

## CI

Push เปรียบเทียบกับ before SHA; PR เปรียบเทียบกับ base SHA; checkout ประวัติครบ
ขั้น plan (`shell: pwsh`) ตรวจ base ด้วย `git cat-file -e <sha>^{commit}`; ว่างหรือหาไม่พบ (เช่นหลัง force-push) ใช้ `--scope all`
Base เป็นศูนย์ทั้งหมด (push แรก) ยังผ่าน `--changed --base` ซึ่ง check.py ถือเป็น full gate
MD-only ไม่เริ่ม CI ตาม paths-ignore; docs ที่ติดมากับโค้ดไม่เพิ่ม scope
เลือกติดตั้ง Node เฉพาะ UI/TypeScript/Extension/build/browser และ Chromium เฉพาะ E2E/extension-smoke/full
ติดตั้ง browser_extension dependencies ตาม needs_extension; ไม่เพิ่มขั้นนี้ให้ UI-only checks
Code ที่รู้จักเลือกตาม mapping; dependency/workflow/ไฟล์ไม่รู้จักใช้ all; สั่ง workflow_dispatch เพื่อ full gate ได้
Push ใหม่ยกเลิก CI เก่าของ ref เดียวกันที่ยังไม่จบ
ไฟล์รายงาน `build/check-plan.json` และ `build/checks/` แนบเป็น CI artifacts
การรอเครื่อง CI/ติดตั้ง dependencies ยังเป็นเวลาเพิ่มจากตัวเทส; ไม่ใช่เป้าหมายวินาทีเดียวกัน

รอบที่เพิ่ม selector นี้เปลี่ยน workflow จึงเข้าเงื่อนไข all บน CI; ไม่ใช่ตัวอย่างเวลา CI ของการแก้ฟีเจอร์เล็ก
หลักฐานในเครื่อง: [Verification focused tests](../delivery/verification-focused-tests.md)
