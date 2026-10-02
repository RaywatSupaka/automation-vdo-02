# Current project status

Desktop foundation: **0.1.0** · Extension/helper: **0.1.1** · schema: **0003** · branch: **dev**

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
กรอก/ย้อนกลับ/ตรวจรายละเอียดและ Autosave ได้; ยังไม่ส่งสร้างสื่อ และยังไม่รวมใน main EXE เดิม
UI ใช้สี/โลโก้/ไอคอนเดิม และ stepper แบบวงกลมเชื่อมกัน: [Branding verification](verification-story-branding.md)
เพิ่มรายละเอียดฟอร์มจากระบบเดิมครบหมวด พร้อม `*` แดงตามเงื่อนไข: [รายการช่อง](../architecture/story-form.md)
เก็บสำเนาไฟล์และค่าต่าง ๆ ในเครื่องได้ แต่ยังไม่เชื่อม provider; [หลักฐานทดสอบ](verification-story-details.md)
[Draft API + Autosave](../architecture/draft-api.md) มี import/restore/close flush และ migration backup/rollback
[Extension pairing](../architecture/extension-foundation.md) มี nonce/DPAPI/scoped token/revoke และ compiled native helper
ตรวจ real Chrome/native/API ด้วย profile แยกแล้ว; ดู [P2 verification](verification-autosave-pairing.md)

## ยังไม่ทำ

Provider adapter/dispatch ผ่าน Extension, การสร้างวิดีโอ, Story/Product/Drama ครบฟีเจอร์,
installer, code signing, automatic update และ remote support
รุ่นนี้เป็นฐานพัฒนาใหม่ ยังไม่แทนโปรแกรมผลิตสื่อเดิม

## เปิดอ่านต่อเฉพาะงาน

- หลักฐาน source, browser และ EXE: [Verification 0.1.0](verification-0.1.0.md)
- งานถัดไปและเกณฑ์เสร็จ: [Foundation plan](../planning/foundation.md)
- แผน workflow และ Extension ที่ยังไม่ implement: [Story Shorts + Extension](../planning/story-shorts.md)
- วิธีเปิดและพัฒนา: [Setup](../development/setup.md)

อัปเดตไฟล์นี้เมื่อความสามารถหรือข้อจำกัดเปลี่ยน ไม่สะสมรายงานและประวัติทุกรุ่นที่นี่
