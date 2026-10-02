# Verification: Story Shorts details

Scope: เพิ่มรายละเอียดฟอร์มเดิมใน wizard ใหม่ และช่องบังคับ `*` สีแดง
รายการความสามารถ/ข้อจำกัด: [Story form](../architecture/story-form.md)

## Commands และผล

ใช้ `.venv\Scripts\python.exe` ใน root โปรเจกต์ใหม่

| Command | ผล | เวลารวม wrapper |
|---|---|---|
| `tools/check.py --scope ui build-ui` รอบแรก: ui | 21 passed | 19.665 s |
| รอบแรก: build-ui | ไม่ผ่าน TS2339 ใน test: inferred draft type ไม่ครอบคลุม videoMode | 13.708 s |
| คำสั่งเดิมหลังแก้ annotation: ui | 21 passed, Vitest 392 ms | 1.509 s |
| หลังแก้: build-ui | TypeScript และ Vite ผ่าน | 21.104 s |
| `tools/check.py --scope e2e --match "Story wizard"` | 4 passed, Playwright 11.3 s | 17.883 s |

ไม่มี full backend suite เพราะเปลี่ยนเฉพาะ UI; ไม่ build EXE หรือเรียก provider จริง
ข้อผิดพลาดรอบแรกเป็น type ใน test และแก้ก่อนผลเขียว ไม่ปกปิดผลเดิม

## พฤติกรรมที่ตรวจ

- Navigation, validation, dirty/completion และ permission/session boundary เดิม
- คลิปเดียว/หลายคลิป เก็บค่าเมื่อสลับโหมด จำกัด 10 หัวข้อ และชื่อซ้ำมีคำเตือน
- จำนวนฉาก 6–15, custom style บังคับ, optional duration และไฟล์ตามเงื่อนไข
- ชนิด/จำนวนไฟล์ไม่ถูกต้อง, ฉากปกเกินจำนวนฉาก และจำนวนเพลงเกินไฟล์ที่เลือก
- Provider warnings ไม่เปลี่ยนค่าเอง; field IDs ไม่ซ้ำและ default arrays ไม่แชร์ข้าม draft
- Browser ตรวจ `*` สีแดงและ aria-required, 12 โครงเรื่อง/8 สไตล์/12 ธีมซับ
- เลือกไฟล์จำลอง รูปแบบภาพ/model/ซับ และ review แสดงชื่อไฟล์กับค่าที่เลือก
- SmartSub catalog ถูกปิดใช้งาน; ไม่มี POST จากการกรอกหรือยืนยันแบบร่าง
- Layout 1366×768, 1024×600, 390×844; footer อยู่ในจอ เลื่อนเนื้อหาด้านใน และ stepper เชื่อมวงกลม
- ตรวจ screenshot ขั้นเรื่อง/สไตล์/ภาพวิดีโอ/เสียง เห็นหมวดแบบพับได้และช่องบังคับ

## ขอบเขตหลักฐาน

เป็น source UI และ browser fixtures; ไฟล์ตัวอย่างไม่ได้ผ่านการ decode/render
ไม่มีการอัปโหลด เรียก SmartSub/ChatGPT/Gemini/Flow/Meta หรือสร้างงานจริง
หน้าต่าง native Dev เดิมมีแบบร่างของผู้ใช้ จึงไม่ reload/restart เพื่อป้องกันข้อมูลหาย
การเปิดใช้งานในหน้าต่างเดิมยังรอผู้ใช้จัดการแบบร่าง; EXE เดิมยังไม่รวมการเปลี่ยนแปลงนี้
ผล screenshot อยู่ใน `frontend/test-results/` ที่ Git ignore; ไม่จัดส่งไฟล์ทดสอบให้ลูกค้า
