# Verification: draft API and Extension foundation

Scope: P0/P1 foundation slice; [Draft API](../architecture/draft-api.md), [Extension](../architecture/extension-foundation.md)
ยังไม่ใช่การส่งมอบ autosave, pairing, bridge dispatch หรือ provider จริง

## Focused checks ระหว่างพัฒนา

| Command ผ่าน tools/check.py | ผล | Wrapper time |
|---|---|---|
| `--scope story-api migration bridge-contract` | 48 passed | 6.298 s |
| `--scope auth api-core tooling ui` ฝั่ง Python | 51 passed | 7.064 s |
| คำสั่งข้างต้นฝั่ง UI รอบแรก | 21 passed, 1 failed: test อ้าง registry ย้อน directory เกินหนึ่งระดับ | 6.868 s |
| `--scope ui --match "draft persistence contract"` หลังแก้ path | 1 passed, 21 skipped | 1.490 s |
| `--scope extension-unit build-extension` รอบแรก | unit 5 passed; typecheck ไม่ผ่าน unknown payload และ possibly undefined mock call | 11.767 / 13.817 s |
| `--scope build-extension` หลังแก้ types | typecheck/build ผ่าน | 2.484 / 2.220 s |

Smoke รอบแรกพบ sender guard ปฏิเสธ popup ของตัวเองที่เปิดเป็นแท็บ
แก้ guard ให้ยืนยัน Extension ID + exact popup URL ทั้งสองรูปแบบ โดยยังปฏิเสธเว็บ/content script
เพิ่ม regression case สำหรับ popup แบบแท็บ และตรวจซ้ำใน full gate ด้านล่าง

## Full gate หนึ่งรอบหลังรวมการเปลี่ยนแปลง

ใช้ `.venv\Scripts\python.exe tools/check.py --scope all`
เหตุผล: เพิ่ม schema/migration, permissions/routes, tool selector/CI และ Extension ใหม่ที่เกี่ยวข้องกัน

| Scope | ผล | Wrapper time |
|---|---|---|
| lint | passed | 0.166 s |
| backend | 126 passed; pytest 13.32 s | 14.911 s |
| ui | 22 passed; Vitest 566 ms | 1.849 s |
| build-ui | TypeScript/Vite passed | 31.068 s |
| e2e | 8 passed; Playwright 23.0 s | 26.928 s |
| extension-unit | 5 passed; Vitest 570 ms | 2.273 s |
| extension-typecheck | passed | 3.702 s |
| build-extension | passed | 1.988 s |
| extension-smoke | popup/probe in owned Chromium passed | 2.147 s |

รวมเวลาของ scope 85.132 วินาที; build UI และ browser ใช้เวลาส่วนใหญ่ เกินเป้าหมาย full 60 วินาที
ไม่ใช้ full run เป็นค่าเริ่มต้นของการแก้รายช่อง; มี scopes เล็กตามตาราง focused checks
มี dependency deprecation warning เดิมจาก Starlette/httpx; ไม่มี test failure ใน full gate
ผล JSON และภาพอยู่ใน `build/checks/`, `build/extension-smoke/` ที่ Git ignore
ตรวจภาพ popup แล้วข้อความสถานะตรงกับความสามารถจริง ไม่แสดง paired/ready

## หลักฐานที่พิสูจน์แล้ว

- แบบร่างไม่ครบ 95 ช่องถูกเติม default และคืนหลังสร้าง API instance ใหม่ โดยไม่มี job ใหม่
- Duplicate create/update คืน ACK เดิม; concurrent writers หนึ่งรายสำเร็จ อีกคน conflict
- Scope ownership, token/role/dev bypass ถูกบังคับ; support ไม่เห็น draft content
- Draft/command/event atomic; event write ล้มเหลวแล้วไม่เหลือ partial draft
- WAL backup อ่านข้อมูลเดิมได้; migration failure rollback ทั้ง DDL และข้อมูล ไม่ restore ทับ live DB
- Native process stdout เป็น framed JSON; reject malformed/oversize/version/origin/unknown command
- Extension load จริงใน Chromium profile ชั่วคราว; helper ที่ไม่ลงทะเบียนแสดง disconnected
- App UI เดิมและ auth/workflow regressions ผ่าน โดยไม่มี provider request จริง

## ยังไม่พิสูจน์หรือยังไม่ทำ

- ไม่ได้ migrate ฐานข้อมูลของโปรแกรมผู้ใช้ที่เปิดค้างอยู่; ตรวจด้วย sandbox DB เท่านั้น
- ไม่ได้ register native host, install ใน Chrome ของผู้ใช้, จับคู่, ออก credential หรือเรียก ChatGPT
- Native host ทดสอบเป็น Python subprocess; ไม่ใช่ compiled helper/installed Windows proof
- ไม่ build EXE/installer รอบนี้; packaging spec เพิ่ม registry JSON แต่ยังไม่มี packaged activation proof
- ฟอร์ม desktop ยังเป็น in-memory draft; autosave/import/close flush ยังต้องทำในรอบถัดไป
- ไม่มีการเปลี่ยน UX/UI ของโปรแกรมหลักในรอบนี้ จึงเก็บหน้าต่างที่มีแบบร่างเดิมไว้
- Popup ใหม่ตรวจใน owned browser แล้วปิด context; ระบบเก่าและ session ของผู้ใช้ไม่ถูกรีสตาร์ต
