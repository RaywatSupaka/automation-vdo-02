# Story Shorts form details

## ขอบเขต

แบบร่างมี local API/Autosave/import แล้ว; ยังไม่มี provider หรือ render ดู [Draft API](draft-api.md)
ออกแบบ React ใหม่โดยอ่านฟอร์มเก่าเป็น reference และใช้เฉพาะค่า/ชื่อ option ที่เปิดเผยใน UI
ไม่คัดลอก controller, prompt, MD, job, credentials หรือข้อมูลลูกค้า
ค่าของ model เป็นรายการอ้างอิงจาก source เก่า ไม่ใช่การรับรองความสามารถของบัญชีปัจจุบัน
ขอบเขต workflow ที่จะทำจริงทีละ feature อยู่ใน [Story plan](../planning/story-shorts.md)

## รายการเทียบฟอร์มเดิม

ชื่อไฟล์ในคอลัมน์ท้ายเป็น source ในโปรเจกต์เดิมที่อ่านเป็น reference ไม่ใช่ dependency

| หมวดใหม่ | รายละเอียด | Reference เดิม |
|---|---|---|
| เรื่อง | คลิปเดียว/ชุดไม่เกิน 10 หัวข้อ รายละเอียดแยกจากหัวข้อ รูปหลัก และกลุ่มผู้ชม | `web_ui/index.html`, batch dialog |
| การเล่า | ผู้บรรยาย/พูดคนเดียว/สนทนา/เล่าด้วยภาพ โครงเรื่อง 12 แบบ โทน hook ตอนจบ CTA ตัวอย่างแนวทาง | `storytelling.js`, `core/creative_brief.py` |
| ภาพ | สไตล์ 8 แบบ รวมกำหนดเอง พร้อมรายละเอียดภาพ | `core/story_styles.py` |
| Provider | ChatGPT/Gemini, model, ภาพเคลื่อนไหว/Flow/Meta, ฉาก 6–15 ค่าเริ่มต้น 10, เป้าหมายเวลา | `index.html`, `core/ai_web_models.py` |
| Flow | Model, Frames/Ingredients, resolution, duration, ตัวละครสมมติ | `flow_settings.js`, `flow_motion.js` |
| Motion | ความแรงการเคลื่อนไหว และช่วงเปลี่ยนฉาก | `index.html` |
| ปก | เปิดปก AI เลือกฉาก หัวเรื่อง คำเน้น ธีม และตำแหน่งข้อความ | `ai_cover.js`, `clip_cover.js` |
| อินโทร | เปิดใช้และเลือกไฟล์วิดีโอ | `video_intro.js` |
| กรีนสกรีน | เปิดใช้ เลือก 1–3 ไฟล์ จัดลำดับ ความทึบ contain/cover | `green_screen.js` |
| โลโก้ | ไฟล์ ความทึบ ขนาด ตำแหน่ง ระยะขอบ และ X/Y | `index.html`, logo settings |
| เสียง | SmartSub/เสียงคลิป/ไม่มีเสียง ไฟล์เสียงอ้างอิง reference ID ภาษา อารมณ์ ความเร็ว silence format บทพากย์ เสียงคลิปและระดับเสียง allow silent | `media_audio.js`, voice settings |
| ซับ | ภาษา พยางค์ ธีม 12 แบบ animation 9 แบบ ฟอนต์/ไฟล์ ขนาด ช่องไฟวรรณยุกต์ เส้นขอบ ตำแหน่ง สี และพื้นหลัง | `index.html`, `core/subtitle_styles.py` |
| เพลง | ไฟล์หลายเพลง จำนวนเพลงต่อคลิป ระดับเสียง ช่วงเปลี่ยนเพลง และ ducking | `music_library.js`, music settings |
| SFX | วิธีเลือก ไฟล์ ระดับเสียง ช่วงห่าง และจำนวนสูงสุด | `index.html`, SFX settings |
| ดนตรี AI | เปิดใช้ อารมณ์เพลง และความถี่ | `media_audio.js` |
| Automation | พักตรวจบทก่อนสร้างภาพ และเก็บเข้าคิวอย่างเดียว | `queue_choice.js`, Story workflow |

หัวเรื่องปกจำกัด 40 ตัวอักษรสำหรับแบบร่างปก AI; ยังไม่มี editor แก้ภาพปกหลังสร้าง
กลุ่มผู้ชมและเป้าหมายเวลาเป็นช่องจากฟอร์มใหม่ที่คงไว้ร่วมกับรายละเอียดเดิม
รายชื่อเสียงจริง เครดิต ฟังตัวอย่าง พรีวิว/render คลังสื่อ และบันทึกค่าเริ่มต้นยังไม่พร้อม
ปุ่มที่ต้องพึ่งบริการแสดงว่าไม่พร้อม; ไม่สร้างรายชื่อเสียงปลอมและไม่รับ API key ในฟอร์มนี้
ตัวควบคุมเก่าที่ซ่อน/เลิกใช้ไม่เพิ่มซ้ำ เช่น checkbox นักแสดงที่แทนด้วยโหมดผู้พูดแล้ว

## ข้อมูลและ validation

- ใช้ `*` สีแดงกับช่องบังคับ พร้อม `aria-required`; ตรวจเฉพาะช่องที่ใช้งานตามเงื่อนไข
- หัวข้อบังคับตามโหมดคลิปเดียว/หลายคลิป และสไตล์กำหนดเองต้องกรอกคำอธิบาย
- เปิดอินโทร/กรีนสกรีน/โลโก้/เพลง/SFX แล้วต้องเลือกไฟล์ที่เกี่ยวข้อง
- ตรวจชนิดไฟล์ จำนวน ขนาดสูงสุด 500 MB ต่อไฟล์ และช่วงค่าตัวเลขใน UI
- ไฟล์นำเข้าเป็นสำเนาในเครื่องและเก็บ asset IDs ในแบบร่าง; ไม่ส่งบริการภายนอก ไม่บันทึก original path/log
- สลับตัวเลือกหรือย้อนขั้นแล้วเก็บค่าที่กรอกไว้; หน้า review แสดงเฉพาะค่าที่อยู่ในเงื่อนไขปัจจุบัน
- ตั้งค่าที่ขัดกันจะแสดงข้อสังเกต ไม่เปลี่ยน provider/เสียงโดยพลการ และยังไม่มีการ dispatch
- แบบร่าง ขั้นล่าสุด และไฟล์ที่ backend ACK แล้วกลับมาเมื่อปิด/reload ตาม [Autosave](draft-api.md); edits ที่ยังไม่มี ACK ไม่รับรอง
- ช่องหลายไฟล์ (musicFiles, sfxFiles, greenFiles) เพิ่มไฟล์ใหม่ต่อจากเดิม ข้ามไฟล์ซ้ำที่ name/size/lastModified ตรงกัน
- ช่องไฟล์เดียวแทนที่ไฟล์เดิม; เลือกไฟล์เดิมซ้ำหรือยกเลิก picker ไม่เปลี่ยนค่าและไม่ autosave
- ไฟล์ที่กู้คืนหลัง reload ไม่มี lastModified จึงเลือกไฟล์เดียวกันซ้ำได้; ปุ่ม `เอาออก` เอาออกทีละไฟล์
- Input ถูกล้างทุกครั้งเพื่อเลือกไฟล์ที่เพิ่งเอาออกได้อีก; กรีนสกรีนเกิน 3 ไฟล์แจ้งใน validation ไม่ตัดทิ้งเงียบ ๆ
- Backend validate ค่า/สิทธิ์เองและคืน issues ตอนบันทึก; UI validation เป็น UX hint ไม่ใช่ security boundary

## Source และการตรวจ

- [Field schema](../../frontend/src/features/story-shorts/fields.ts): หมวด ช่อง เงื่อนไข ค่าเริ่มต้น และข้อจำกัด
- [Option catalog](../../frontend/src/features/story-shorts/catalog.ts): label/value ที่อ้างอิงจากฟอร์มเดิม
- [Field renderer](../../frontend/src/features/story-shorts/StoryFields.tsx): input, required mark, ไฟล์และ review display
- [File picks](../../frontend/src/features/story-shorts/file-picks.ts): `mergeFilePicks`/`applyFilePick`; เทส [file-picks.test.ts](../../frontend/src/features/story-shorts/file-picks.test.ts) scope `ui`
- [Draft validation](../../frontend/src/features/story-shorts/draft.ts): feedback และ compatibility warnings
- [ผลทดสอบ](../delivery/verification-story-details.md): focused unit/browser และข้อจำกัดการเปิดใช้งาน
