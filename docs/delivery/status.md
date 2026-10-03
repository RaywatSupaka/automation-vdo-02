# Current project status

Desktop foundation: **0.1.0** · Extension/helper: **0.2.0** · schema: **0004** · branch: **dev**

## ทำแล้ว

React desktop UI, authenticated FastAPI, SQLite migration, supervised worker,
durable simulator workflow, guarded resume/reconciliation, error catalog,
structured logs, read-only DB inspection, support ZIP และ offline doctor
มีเครื่องมือทดสอบและ build portable Windows
F1 ใน source: typed API/error contracts, command trace, pagination และ privacy validation
ตรวจการทำงานร่วมกับ frontend เดิมแล้ว ดู [Verification F1](verification-f1.md)
เพิ่ม authentication/permission boundary, role matrix, support token และ dev identity bypass ที่ไม่ข้ามสิทธิ์
หน้าจอแสดงปุ่มตาม permissions; account login/license ยังไม่ implement ดู [Security](../operations/security.md)
EXE 0.1.0 ที่ build ก่อนหน้านี้ยังไม่รวม F1/permissions; source Dev กับ packaged build เป็นคนละหลักฐาน
UI แบบร่าง Story Shorts แบบ 5 ขั้นพร้อม shared component อยู่ใน source แล้ว: [Step wizard](../architecture/step-wizard.md)
กรอก/ย้อนกลับ/ตรวจรายละเอียดและ Autosave ได้; ขั้นตรวจรายละเอียดเริ่มงานจำลองและติดตามผลได้ แต่ยังไม่สร้างสื่อจริงและยังไม่รวมใน main EXE เดิม
UI ใช้สี/โลโก้/ไอคอนเดิม และ stepper แบบวงกลมเชื่อมกัน: [Branding verification](verification-story-branding.md)
เพิ่มรายละเอียดฟอร์มจากระบบเดิมครบหมวด พร้อม `*` แดงตามเงื่อนไข: [รายการช่อง](../architecture/story-form.md)
เก็บสำเนาไฟล์และค่าต่าง ๆ ในเครื่องได้ แต่ยังไม่เชื่อม provider; [หลักฐานทดสอบ](verification-story-details.md)
[Draft API + Autosave](../architecture/draft-api.md) มี import/restore/close flush และ migration backup/rollback
[Extension pairing](../architecture/extension-foundation.md) มี nonce/DPAPI/scoped token/revoke และ compiled native helper
ตรวจ real Chrome/native/API ด้วย profile แยกแล้ว; ดู [P2 verification](verification-autosave-pairing.md)
P3 ใน source: สร้างงาน `story_simulated` จาก draft revision ที่ snapshot แล้ว ให้ Extension ที่จับคู่รับงานผ่าน `POST /api/browser/work`
ผลเป็นข้อความจำลองเท่านั้น; ผ่าน `--scope all` แต่ helper 0.2.0 ต้อง build/register ใหม่ก่อนใช้กับ Chrome จริง
F2 ใน source: health แยก worker alive/ready/stalled จาก heartbeat และ restart worker ที่ค้างภายในโควตาเดิม
Autosave ไม่ค้างเมื่อถูกปฏิเสธ และ draft รายงาน `FIELD_REQUIRED`/`DRAFT_ASSET_MISSING` จาก backend: [Draft API](../architecture/draft-api.md)
P4 ใน source Dev: ปุ่มเริ่มงานจำลองจาก revision ที่บันทึกแล้ว, สถานะ/ผลพร้อมป้าย `SIMULATION`,
คำสั่งตรวจผลเดิม/ยกเลิกตามสิทธิ์ และรุ่น Extension/helper ที่ API คาดหวัง; E2E fixture ผ่าน 12 เคส
งานจำลองจากหน้าต่าง Dev ผ่าน Chrome profile ของเจ้าของเสร็จใน 20 วินาที ส่งครั้งเดียว; ดู [P4 verification](verification-p4.md)
งานสำรอง B1–B5 แก้ขอบเขต scenario, การ migrate ตอนเริ่ม, pairing หมดอายุ, การอ่านตัวเลข และจำนวนไฟล์ใน UI แล้ว; ดู [P4 verification](verification-p4.md#งานสำรอง)

## ยังไม่ทำ

Provider จริงผ่าน Extension (ตอนนี้ dispatch แบบจำลองเท่านั้น), การสร้างวิดีโอ, Story/Product/Drama ครบฟีเจอร์,
installer, code signing, automatic update และ remote support
รุ่นนี้เป็นฐานพัฒนาใหม่ ยังไม่แทนโปรแกรมผลิตสื่อเดิม

## ข้อจำกัดที่ทราบ (ยังไม่แก้)

- งานที่ cancel แล้วยังถูก resume กลับเข้าคิวได้
- `/api` ที่ไม่มี route/method ผิด/JSON เสีย ตอบ 404/405/422 ก่อนตรวจ token
- Reconcile เรียก provider inspect ใน API process โดยไม่มี timeout ต้องย้ายก่อนต่อ provider จริง
- Native helper รวมทุกความล้มเหลวเป็น `unavailable` และไม่มี log
- ผู้ใช้สิทธิ์อ่านอย่างเดียวยังดูแบบร่างไม่ได้ (ต้องมีโหมดไม่เขียนใน DraftStore)
- Native helper ไม่อยู่ใน `tools/build.py`; main EXE ใน `dist/` ยังเป็น build จาก 5847f79
- `--scope all` ใช้ 136.611 วินาทีในการตรวจงานสำรอง (2026-10-03) เกินเป้า 60 วินาทีใน [Testing](../development/testing.md)
สถานะงานค้างของ P3 อยู่ใน [Coordinated milestones](../planning/story-extension-milestones.md)

## เปิดอ่านต่อเฉพาะงาน

- หลักฐาน source, browser และ EXE: [Verification 0.1.0](verification-0.1.0.md)
- งานถัดไปและเกณฑ์เสร็จ: [Foundation plan](../planning/foundation.md)
- แผน workflow และ Extension ที่ยังไม่ implement: [Story Shorts + Extension](../planning/story-shorts.md)
- วิธีเปิดและพัฒนา: [Setup](../development/setup.md)

อัปเดตไฟล์นี้เมื่อความสามารถหรือข้อจำกัดเปลี่ยน ไม่สะสมรายงานและประวัติทุกรุ่นที่นี่
