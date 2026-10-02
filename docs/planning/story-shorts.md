# Story Shorts: feature plan

**สถานะ: ออกแบบเท่านั้น ยังไม่มี Story workflow หรือ Extension ใหม่ที่ทำงานจริง**
เฉพาะ UI แบบร่าง 5 ขั้นทำใน source แล้ว ดู [Shared step wizard](../architecture/step-wizard.md); ยังไม่เชื่อม Story API
ฟอร์มมีตัวเลือกจากระบบเดิมครบหมวดเพื่อออกแบบล่วงหน้า ดู [รายการช่อง](../architecture/story-form.md)
การเลือก Gemini/Flow/Meta, ตัวละครสนทนา หรือเสียงในแบบร่าง ไม่ได้หมายถึงมี adapter ใช้งานแล้ว
ใช้พฤติกรรมของงานเก่าเป็น reference; เอกสารนี้เขียนใหม่ ไม่ย้าย source, MD หรือข้อมูลลูกค้า

## ผลลัพธ์ที่ต้องการ

หัวข้อ → บทและแผนฉาก → ภาพจาก ChatGPT Web → เสียงพากย์ → Short แนวตั้ง
ChatGPT Web ใน workflow นี้รับผิดชอบบทและภาพ; เสียงกับการประกอบวิดีโอเป็น adapter แยก
ดู [สิ่งที่เรียนรู้จากระบบเดิม](story-reference.md) สำหรับหลักฐานจาก source

| รายการ | ขอบเขตรุ่นแรกที่เสนอ |
|---|---|
| ประเภท | เรื่องเล่าไทย ผู้บรรยายหนึ่งคน; ยังไม่ทำตัวละครพูดโต้ตอบ |
| ค่าเริ่มต้น | 10 ฉาก ปรับ 6–15 ตามฟอร์มเดิม; เป้าหมาย 45 วินาที ปรับ 30–60 หรือเว้นว่าง ไม่ใช่ข้อจำกัดแพลตฟอร์ม |
| รูปแบบ | 9:16, เป้าหมาย 1080×1920, ภาพนิ่งแพน/ซูมด้วย FFmpeg ในเครื่อง |
| บท | ชื่อเรื่อง, hook, เรื่อง, ตอนจบ, คำบรรยายรายฉาก, visual bible และ image prompt |
| ภาพ | สร้างทีละฉาก ผูกกับ revision และ reference ที่ยืนยันเจ้าของได้ |
| เสียง | TTS adapter แยก; SmartSub เป็นตัวเลือกตามงานเก่า ต้องตรวจ API และสิทธิ์ใช้งานใหม่ |
| ผลส่งออก | MP4 H.264/AAC, ซับ, ภาพปกจากฉากที่บันทึก และ metadata ของงาน |

ยังไม่รวม Flow/Meta video, lip sync, Product/Drama, โพสต์อัตโนมัติ และหลายซีรีส์
ออกแบบ adapter รองรับการเพิ่มภายหลัง แต่ไม่ทำทุก provider พร้อมกัน

## หน้าจอและ automation

1. กรอกหัวข้อ/เรื่อง ตั้งจำนวนฉาก ระยะเวลา โทน และผู้ให้เสียง แล้วเริ่มงาน
2. แสดงบทและ scene cards พร้อมสถานะภาพ/เสียงแต่ละฉาก
3. ค่าเริ่มต้นทำต่ออัตโนมัติเมื่อ schema และเงื่อนไขผ่าน; มีตัวเลือกพักตรวจบทก่อนสร้างภาพ
4. การแก้บทสร้าง revision ใหม่; คงไฟล์เก่าและใช้ผลเดิมเฉพาะเมื่อ dependencies ตรงกัน
5. ข้อผิดพลาดแสดงขั้นตอน รหัส เหตุผลที่ปลอดภัย และการกู้คืนที่ระบบกำลังทำ
6. หน้าผลลัพธ์แสดงไฟล์ที่ตรวจแล้ว; ปุ่มสร้างใหม่เป็นเจตนาใหม่ ไม่ใช่ retry คำขอไม่แน่ใจ

## Milestones ที่ส่งตรวจแยกกัน

| ขั้น | ผลที่ตรวจได้ | Gate |
|---|---|---|
| S0 | Story schema, revision, API permissions, UI ด้วย fixtures | unit/API; F3 ก่อน migration ของข้อมูลจริง |
| E0 | Extension ใหม่จับคู่กับแอป, handshake และจำลอง command/result | bridge/auth/duplicate contracts |
| S1 | ChatGPT Web สร้างบทจริงหนึ่งงานและบันทึกแผน | F2 readiness/recovery และ browser ownership ผ่าน |
| S2 | สร้างภาพจริงหนึ่งฉาก แล้วขยายเป็นหลายฉากพร้อม resume | send uncertainty, stale tab, artifact checks |
| S3 | เพิ่มเสียงจาก adapter ที่ยืนยัน API แล้ว | receipt, acceptance, duration และไม่คิดงานซ้ำ |
| S4 | ประกอบภาพ+เสียง+ซับและส่งออก Short | ตรวจวิดีโอจริงและ scene coverage |
| S5 | ชุดโปรแกรมกับ Extension สำหรับเครื่องลูกค้า | F4/F5, version pairing, clean Windows และ release tests |

**Milestone แรกสำหรับใช้งานตรวจเนื้อหาคือ S1–S2: บทและภาพ**
ยังห้ามแสดงว่า Short เสร็จจน S3–S4 ให้เสียงและไฟล์วิดีโอที่ตรวจแล้ว
พัฒนา S0 และ E0 ด้วย fixtures ได้ระหว่างทำ foundation; ไม่ต้องรอ installer ก่อนเริ่มออกแบบ domain

## เปิดเอกสารตามงาน

- ข้อมูล/API/สิทธิ์: [Story contracts](story-data-api.md)
- Framework และขอบเขต Extension: [Browser extension](browser-extension.md)
- การส่งคำสั่งและกู้คืน: [Extension protocol](extension-protocol.md)
- เคสและความเร็วการตรวจ: [Story testing](story-testing.md)
- ลำดับ infrastructure: [Foundation](foundation.md)
