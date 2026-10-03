# Shared step wizard and Story Shorts form

**ทำแล้วใน source:** การ์ดกรอกข้อมูลทีละขั้น และแบบร่าง Story Shorts
**ยังไม่ทำ:** สร้างบท/ภาพ/เสียง/วิดีโอจริง; Story มี [Autosave/API](draft-api.md) แล้ว

## Component กลาง

Source: [StepWizard](../../frontend/src/components/step-wizard/StepWizard.tsx),
[navigation state](../../frontend/src/components/step-wizard/state.ts),
[layout](../../frontend/src/components/step-wizard/step-wizard.css)

- รับ `steps` ที่มี stable id, label, title, description, render และ optional validate
- รับ finishLabel, completionMessage, footerNote จากหน้าที่ใช้งาน ไม่ผูกชื่อ Story ใน component
- `finishAction` (ไม่บังคับ) แทนการยืนยันที่ขั้นสุดท้าย: ตรวจทุกขั้นก่อน แล้วเรียก action ของ host; ใช้ label/disabled ของ host
- เก็บเฉพาะ active/completed/confirmed; ข้อมูลฟอร์มและกติกาของ feature อยู่ที่ host
- Host เรียก markChanged เมื่อแก้ข้อมูล เพื่อยกเลิก completion ของขั้นนั้นและขั้นถัดไป
- กดกลับได้เฉพาะขั้นที่ผ่านแล้ว; ไปข้างหน้าต้อง validate ตามลำดับ
- ตรวจขั้นก่อนหน้าด้วยก่อนยืนยัน; กลับไปดูข้อมูลโดยไม่แก้ไม่ล้างผลตรวจ
- Confirmation เป็นสถานะตรวจรายละเอียดใน UI ไม่ใช่หลักฐาน API บันทึกหรือสร้างงานสำเร็จ
- ไม่มีการยิง API หรือ persist ใน component; Story host จัดการ async start, pending/error และ idempotency แยกจาก wizard

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
| 5 ตรวจรายละเอียด | สรุปข้อมูล; ปุ่มขวาล่างเป็น `เริ่มงานจำลอง` เมื่อมีสิทธิ์ (ไม่มีสิทธิ์ = ยืนยันแบบร่างเหมือนเดิม) |

ค่าเริ่มต้น 10 ฉาก/45 วินาที; ฉาก 6–15 ตามฟอร์มเดิม ส่วนเวลา 30–60 วินาทีเป็นเป้าหมายที่เว้นว่างได้
รายการช่องและขอบเขตที่ยังเป็นแบบร่าง: [Story form details](story-form.md)
ช่องบังคับแสดง `*` สีแดง; เมื่อเปิดตัวเลือกที่ต้องใช้ไฟล์ ช่องไฟล์นั้นจะบังคับตามเงื่อนไข
Validation นี้ให้ feedback ผู้ใช้; Story API ตรวจ schema/issues และ revision ซ้ำก่อนสร้างงานจำลอง
ยังไม่มี voice selector จริง; ไม่แสดงรายชื่อเสียงหรือ provider ว่าเชื่อมแล้ว
แบบร่างมี Autosave/restore; wizard รับ initialStep และ onStepChange เพื่อเก็บขั้นล่าสุด
ข้อมูลที่บันทึกสำเร็จคืนจาก API เมื่อเปิดใหม่; close guard รอ flush และไม่ปิดเมื่อ save ล้มเหลว
ไม่ส่งเนื้อหาไป log/localStorage; session หมดอายุหรือสิทธิ์ถูกถอนจะ unmount และทิ้ง draft ใน memory
Wizard ถอยขั้นที่ผ่านแล้วแต่ตอนนี้ไม่ผ่าน (เช่นไฟล์บังคับหาย) และแจ้ง onStepChange จึง autosave ได้โดยไม่มี edit
ดังนั้น `storyAccess()` ให้เมนู Story แสดงเมื่อมี `stories:drafts:read` แต่ mount editor (StoryShorts/DraftStore) เฉพาะเมื่อมี `stories:drafts:write` ด้วย
Viewer เห็น notice แบบ static และป้าย `อ่านอย่างเดียว` (`story-readonly-notice`/`story-readonly`) ไม่โหลด draft; support ไม่เห็นเมนู
ทุก session ที่เขียนได้ mount editor ซึ่งตั้ง `window.smartflowFlush` จึงให้ close guard ถือว่าไม่มี flush = ไม่มีค่าค้างได้
Server issues แสดงใต้สถานะบันทึกตาม [Draft API](draft-api.md); validation ใน wizard เป็น UX hint
ปุ่ม `เริ่มงานจำลอง` อยู่ที่ footer ของ wizard (ไม่มีขั้นยืนยันซ้ำ) แสดงเฉพาะ `jobs:create` และปิดเมื่อมี server issues
หรือเริ่มไปแล้วกับ revision นี้ (`เริ่มงานจำลองแล้ว`); host flush ก่อนส่ง, เก็บ key เดิมเมื่อ retry; ผู้ใช้ย้อนกลับไปดูขั้นก่อนหน้าได้เอง
และ poll สถานะทุก 1.5 วินาทีจนจบหรือ unmount; ผลทุกชิ้นติดป้าย `SIMULATION` ไม่ใช่สื่อจริง
`needs_review` แสดงตรวจผลเดิม/ยกเลิกเฉพาะ `jobs:command`; ข้อความ error code อื่นอ่านจาก `/api/errors`

## App navigation

Source: [navigation](../../frontend/src/navigation.ts); `canOpen(view, permissions)` เป็นจุดเดียวที่กำหนดเมนู/view และ fallback
View ที่เลือกเก็บต่อ tab ใน sessionStorage key `smartflow-view` (ไม่ใช้ URL fragment ซึ่งเป็นของ `#token`); อ่านไม่ได้ใช้ `jobs`
Poll แรกย้าย view ที่ไม่มีสิทธิ์ไปตามลำดับ jobs, database, logs, story, browser; ไม่มีสิทธิ์เลยคงที่ `jobs`; `#token` ใหม่รีเซ็ตเป็น `jobs`
`/health` และ `/session` ทุก 1.5 วินาที; `/jobs` และ events เฉพาะ view jobs; diagnostics เฉพาะ view database/logs ที่เปิดอยู่
View ที่ไม่มีสิทธิ์ redirect โดยไม่ fetch ข้อมูล และล้าง rows ของสิทธิ์ที่ถูกถอน; poll ที่ได้ข้อมูลเดิมไม่ re-render
StoryShorts element ถูก memoise เพื่อไม่ให้ poll re-render wizard

## ตรวจเฉพาะส่วน

- Unit navigation/validation: [state tests](../../frontend/src/components/step-wizard/state.test.ts), [draft tests](../../frontend/src/features/story-shorts/draft.test.ts)
- สิทธิ์/view/poll ราย role: [navigation tests](../../frontend/src/navigation.test.ts); Vitest รวมเฉพาะ `src/**/*.test.ts` ไม่รวม `.test.tsx`
- Browser behavior/layout/session: [wizard tests](../../frontend/e2e/story-wizard.spec.ts)
- `python tools/check.py --scope ui build-ui` แล้ว `--scope e2e --match "Story wizard"`
- ใช้ frontend mapping เดิมใน [selector](../../tools/check_selection.py); ไม่ต้องทดสอบ backend ทั้งหมด

ขอบเขต feature จริงและ persistence ถัดไป: [Story plan](../planning/story-shorts.md)
หลักฐานล่าสุด: [Story details verification](../delivery/verification-story-details.md)
