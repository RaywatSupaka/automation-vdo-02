# Shared step wizard and Story Shorts form

**ทำแล้วใน source:** การ์ดกรอกข้อมูลทีละขั้น และแบบร่าง Story Shorts
**ยังไม่ทำ:** บันทึกแบบร่างลง DB, Story API, สร้างบท/ภาพ/เสียง/วิดีโอจริง

## Component กลาง

Source: [StepWizard](../../frontend/src/components/step-wizard/StepWizard.tsx),
[navigation state](../../frontend/src/components/step-wizard/state.ts),
[layout](../../frontend/src/components/step-wizard/step-wizard.css)

- รับ `steps` ที่มี stable id, label, title, description, render และ optional validate
- รับ finishLabel, completionMessage, footerNote จากหน้าที่ใช้งาน ไม่ผูกชื่อ Story ใน component
- เก็บเฉพาะ active/completed/confirmed; ข้อมูลฟอร์มและกติกาของ feature อยู่ที่ host
- Host เรียก markChanged เมื่อแก้ข้อมูล เพื่อยกเลิก completion ของขั้นนั้นและขั้นถัดไป
- กดกลับได้เฉพาะขั้นที่ผ่านแล้ว; ไปข้างหน้าต้อง validate ตามลำดับ
- ตรวจขั้นก่อนหน้าด้วยก่อนยืนยัน; กลับไปดูข้อมูลโดยไม่แก้ไม่ล้างผลตรวจ
- Confirmation เป็นสถานะตรวจรายละเอียดใน UI ไม่ใช่หลักฐาน API บันทึกหรือสร้างงานสำเร็จ
- ไม่มีการยิง API หรือ persist ใน component; เมื่อเพิ่ม async submission ต้องมี pending/error/idempotency contract แยก

## Layout และ accessibility

การ์ดกินพื้นที่ที่เหลือใต้หัวหน้าและ topbar โดยไม่ทำหน้าฟอร์มยาวเกินจอ
แถบขั้นตอน/progress และ footer อยู่ประจำที่; เนื้อหาด้านในเลื่อนได้เมื่อยาว
วงกลมอยู่เหนือชื่อขั้น มีเส้นเชื่อมระหว่างวงกลมโดยตรง; ไม่แสดงข้อความนับขั้นหรือ progress track แยก
เส้นเติมสีเมื่อผ่านขั้นนั้น; ค่าจำนวน completion มีเฉพาะ assistive technology รวมขั้นสุดท้ายหลังยืนยัน
ขั้นก่อนหน้ามีเครื่องหมายถูก ขั้นปัจจุบันมี aria-current และขั้นที่ยังไม่ถึงกดไม่ได้
เปลี่ยนขั้นเลื่อนเนื้อหาขึ้นบนและ focus heading; validation error รับ focus และประกาศด้วย role alert
ใช้ปุ่ม/radio/checkbox มาตรฐานสำหรับ keyboard; รองรับ prefers-reduced-motion
จอแคบลดขนาดวงกลมและซ่อนภาพประกอบ แต่คง field, step labels และ navigation
หัวหน้ามีแค่ `เรื่องเล่า short`; สีและ assets ใช้ตาม [Branding](branding.md)
ไม่เปลี่ยนขั้นจาก mouse wheel/swipe เพื่อป้องกันข้ามขั้นขณะเลื่อนอ่านหรือกรอกข้อมูล

## Story Shorts host

Source: [StoryShorts](../../frontend/src/features/story-shorts/StoryShorts.tsx),
[draft validation](../../frontend/src/features/story-shorts/draft.ts), [App](../../frontend/src/App.tsx)

| ขั้น | ข้อมูล |
|---|---|
| 1 เรื่องที่จะเล่า | คลิปเดียว/หลายคลิป หัวข้อ รายละเอียด กลุ่มผู้ชม และรูปหลัก |
| 2 โทนและสไตล์ | ผู้พูด โครงเรื่อง โทน เปิด/จบ CTA และสไตล์ภาพ |
| 3 ภาพและวิดีโอ | Provider/model, 6–15 ฉาก, Flow, motion, ปก อินโทร กรีนสกรีน โลโก้ |
| 4 เสียงและซับ | เสียงพากย์ ซับ เพลง SFX ดนตรี AI และ automation |
| 5 ตรวจรายละเอียด | สรุปข้อมูลและยืนยันการตรวจแบบร่าง |

ค่าเริ่มต้น 10 ฉาก/45 วินาที; ฉาก 6–15 ตามฟอร์มเดิม ส่วนเวลา 30–60 วินาทีเป็นเป้าหมายที่เว้นว่างได้
รายการช่องและขอบเขตที่ยังเป็นแบบร่าง: [Story form details](story-form.md)
ช่องบังคับแสดง `*` สีแดง; เมื่อเปิดตัวเลือกที่ต้องใช้ไฟล์ ช่องไฟล์นั้นจะบังคับตามเงื่อนไข
Validation นี้ให้ feedback ผู้ใช้; Story API ในอนาคตต้อง enforce schema เอง
ยังไม่มี voice selector จริง; ไม่แสดงรายชื่อเสียงหรือ provider ว่าเชื่อมแล้ว
แบบร่างอยู่ใน React memory; เปลี่ยนเมนูไปมาได้ แต่ปิด/reload แล้วข้อมูลหาย มีข้อความแจ้งที่ footer
ไม่ส่งเนื้อหาไป API/log/localStorage; session หมดอายุหรือสิทธิ์ถูกถอนจะ unmount และทิ้ง draft
เมนูเปิดให้ session ที่มี jobs:create; ไม่มี route ใหม่และไม่เปลี่ยน auth/bypass policy

## ตรวจเฉพาะส่วน

- Unit navigation/validation: [state tests](../../frontend/src/components/step-wizard/state.test.ts), [draft tests](../../frontend/src/features/story-shorts/draft.test.ts)
- Browser behavior/layout/session: [wizard tests](../../frontend/e2e/story-wizard.spec.ts)
- `python tools/check.py --scope ui build-ui` แล้ว `--scope e2e --match "Story wizard"`
- ใช้ frontend mapping เดิมใน [selector](../../tools/check_selection.py); ไม่ต้องทดสอบ backend ทั้งหมด

ขอบเขต feature จริงและ persistence ถัดไป: [Story plan](../planning/story-shorts.md)
หลักฐานล่าสุด: [Story details verification](../delivery/verification-story-details.md)
