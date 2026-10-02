# Current project status

Version: **0.1.0 foundation** · branch: **dev**

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

## ยังไม่ทำ

Provider/Extension จริง, การสร้างวิดีโอ, Story/Product/Drama ครบฟีเจอร์,
installer, code signing, automatic update และ remote support
รุ่นนี้เป็นฐานพัฒนาใหม่ ยังไม่แทนโปรแกรมผลิตสื่อเดิม

## เปิดอ่านต่อเฉพาะงาน

- หลักฐาน source, browser และ EXE: [Verification 0.1.0](verification-0.1.0.md)
- งานถัดไปและเกณฑ์เสร็จ: [Foundation plan](../planning/foundation.md)
- วิธีเปิดและพัฒนา: [Setup](../development/setup.md)

อัปเดตไฟล์นี้เมื่อความสามารถหรือข้อจำกัดเปลี่ยน ไม่สะสมรายงานและประวัติทุกรุ่นที่นี่
