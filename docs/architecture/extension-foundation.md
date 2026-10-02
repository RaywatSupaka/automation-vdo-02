# Extension foundation: implemented boundary

โครงใหม่อยู่ใน `browser_extension/`: WXT 0.21.4 + TypeScript + React + Manifest V3
Dependencies pin และมี package-lock; ใช้ Vitest กับ WXT test plugin
ทำแล้ว: background sender guard, popup ตรวจ helper, bounded hello protocol และ Python native framing
ยังไม่ทำ: host registration/installer, pairing/credential, backend bridge, content adapter หรือ ChatGPT จริง
แผนเต็ม: [Extension](../planning/browser-extension.md), [Protocol](../planning/extension-protocol.md)

## ขอบเขตปัจจุบัน

- Permission มี `nativeMessaging` อย่างเดียว ไม่มี host access/content script/clipboard/debugger
- Background รับคำสั่ง probe เฉพาะ popup URL ของ Extension ID ตัวเอง รวมเมื่อเปิด popup เป็นแท็บ
- หน้าเว็บหรือ content script ใช้ handler นี้เป็น proxy ไป native host ไม่ได้
- Host name ใหม่ `com.smartflow.next.dev`; ไม่เกี่ยวกับ identity/host ของระบบเก่า
- Hello protocol version 1, Extension/helper version 0.1.0; รุ่นหรือ field ผิดถูกปฏิเสธ
- Response ต้องตรง message_id และแสดง `unpaired`, capabilities ว่างเสมอ
- Probe มี deadline 5 วินาที ไม่มี retry/send งานผลิตสื่อ; reconnect ต้อง probe ใหม่
- Native framing ใช้ UTF-8 และ uint32 ความยาวแบบ native endian; cap 64 KiB ต่ำกว่า Chrome transport limit
- Native host ตรวจ calling origin ตรงกับ Extension ID ที่กำหนด; stdout มีแต่ framed JSON
- Native helper ยังไม่เก็บ credential ไม่ยิง HTTP และไม่รับ dispatch/shell/path commands

คำว่า `unpaired` หมายถึงตรวจข้อความ hello ผ่านเท่านั้น ไม่ได้ยืนยัน backend พร้อมหรือ provider พร้อม
ยังไม่ install ใน Chrome ของผู้ใช้; smoke ใช้ Chromium กับ profile ชั่วคราวแยกต่างหากแล้วปิดเอง

## คำสั่งตรวจ

ใช้ Python/Node ที่ติดตั้งใน root โปรเจกต์จาก [Setup](../development/setup.md)

```powershell
.venv\Scripts\python.exe tools/check.py --scope bridge-contract extension-unit build-extension
.venv\Scripts\python.exe tools/check.py --scope extension-smoke
```

Smoke ต้องมี Extension build และ Playwright Chromium แล้ว; SETUP ติดตั้ง dependencies ทั้งสองโปรเจกต์
Build output `browser_extension/.output/chrome-mv3` ไม่เข้า Git; ยังไม่ใช่ชุดส่งมอบให้ลูกค้า
P2 จะเพิ่ม native registration, nonce pairing, protected credentials, revoke และ bridge auth จริง
ห้ามใส่ owner token ลง popup/content script เพื่อข้ามงาน pairing ที่ยังไม่ทำ

Source: [WXT config](../../browser_extension/wxt.config.ts), [protocol](../../browser_extension/protocol/index.ts),
[background](../../browser_extension/entrypoints/background.ts), [native host](../../backend/smartflow/native_host.py)
Tests: [unit](../../browser_extension/protocol/protocol.test.ts), [framing/process](../../tests/test_native_host.py),
[owned browser smoke](../../tools/extension_smoke.mjs)
หลักฐาน: [Verification](../delivery/verification-draft-extension-foundation.md)

อ้างอิงการใช้ framework/protocol: [WXT unit testing](https://wxt.dev/guide/essentials/unit-testing),
[Chrome Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
