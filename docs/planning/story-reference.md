# Story Shorts: lessons from the old implementation

**Reference จาก source แบบอ่านอย่างเดียว; ไม่ใช่ contract หรือ source ที่นำเข้ามาในโปรเจกต์ใหม่**
โครงการอ้างอิง: `C:\Users\RaywatSupaka\Documents\ChatGPT\automation-vdo 2`
รายการต่อไปนี้เป็นผลอ่านโค้ด ไม่ใช่การยืนยันว่า installed build จบงานจริงทุกเส้นทาง

| งานเดิมและ source ที่ตรวจ | สิ่งที่เลือกออกแบบใหม่ |
|---|---|
| `core/story_manager.py::create` รับ topic, story_text, scene_count, provider และ video_generation_mode | เริ่ม Story Shorts narrator เท่านั้น แยก domain ออกจาก Product/Drama/long video |
| Planning ใน `core/story_manager.py` ขอ narration, visual_bible, scene prompts และ durations | ใช้ schema ฉากเป็น object ที่มี stable ID ไม่ใช้ parallel arrays |
| `core/story_pipeline.py::STORY_STAGES` แบ่ง ChatGPT, voice, video, finishing | ChatGPT Web เป็น planning/image adapter; voice/render เป็นคนละ boundary |
| `core/storytelling.py` มี narrator/solo/dialogue/visual และเงื่อนไข Flow/Meta | รุ่นแรกเลือก narrator กับ image motion; character dialogue เป็น feature ถัดไป |
| `ui/main_window.py` ใช้ `SmartSubOnlineClient`, voice queue และ external_job_id | สำรวจ SmartSub เป็น TTS adapter ใหม่พร้อม receipt; ไม่ใช้ token หรือบัญชีที่คัดจากระบบเก่า |
| `core/story_video.py::StoryVideoComposer` ใช้ FFmpeg/ffprobe | ประกอบและตรวจวิดีโอในเครื่องลูกค้า ไม่ต้องมี render server สำหรับ MVP |
| `core/story_finisher.py` ทำซับ เสียง และ finishing | แยกการจัดเวลา/ซับจาก UI และวัดจากเสียงจริงก่อน render |
| `tests/test_story_saved_plan_resume.py` ตรวจ saved plan และ ownership | บันทึก revision และผูกทุก artifact ก่อน resume; ห้ามสร้างบทใหม่เพียงเพราะยังไม่มีภาพ |
| `tests/test_story_video.py` ตรวจหลายฉากและรูปแบบวิดีโอ | สร้าง fixture ใหม่ขนาดเล็ก ตรวจสี/เฟรมแต่ละฉากและ metadata ด้วย ffprobe |
| `browser_extension/src/background/service-worker.js` นำเข้า root legacy scripts | สร้าง Extension ใหม่ด้วย WXT/TypeScript และแยก provider adapter ให้ทดสอบได้ |
| Manifest เก่ามีหลาย provider และ permissions กว้าง | ขอสิทธิ์เฉพาะ ChatGPT และสิ่งจำเป็นที่พิสูจน์ใน pilot |

## Failure boundaries ที่ต้องออกแบบตั้งแต่แรก

- ไม่แน่ใจว่าส่งแล้วหรือไม่: เก็บ checkpoint แล้ว inspect คำขอเดิม ห้ามกดส่งซ้ำเอง
- Draft หรือ attachment ค้าง: ตรวจ job/tab/document และเจ้าของ draft ก่อนแก้; ไม่ล้างของผู้ใช้
- UI ยังบอกกำลังสร้างทั้งที่มีภาพ: ตรวจ result ที่สัมพันธ์กับคำขอและบันทึกจริง ไม่เดาจาก Stop button
- ภาพฉากก่อนติดมากับฉากใหม่: ตรวจ reference manifest ของ operation ก่อนส่ง
- ขาด progress: deadline ที่แน่นอนพร้อม error reason; ไม่รอตลอดไป
- ขาด ACK: ส่งผลเดิมซ้ำแบบ idempotent ได้ แต่ไม่ส่ง prompt ใหม่เพื่อชดเชย ACK

## ขอบเขตการย้าย

ไม่ย้าย source/MD/jobs/media/profiles/Extension storage/credentials จากระบบเก่า
Extension ใหม่มี identity และ native host ของตัวเอง ติดตั้งเคียงกันได้
ไม่ reload หรือแก้ Extension เก่าเพื่อทดสอบระบบใหม่
รายละเอียดที่เลือกใช้เป็นแผนใหม่อยู่ใน [Story Shorts](story-shorts.md)
