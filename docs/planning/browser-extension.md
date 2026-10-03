# Browser extension: framework and boundaries

**ทำแล้ว: โครง WXT/popup, native host, dev registration (HKCU) และ pairing/revoke**
**ยังไม่ทำ: installer ลูกค้า, operation dispatch/claim, content adapter และพิสูจน์ live ChatGPT DOM**
Source และขอบเขตปัจจุบัน: [Extension foundation](../architecture/extension-foundation.md)
สร้างใหม่เพราะ source เก่ารวมหลาย provider/legacy scripts; ไม่ย้ายโค้ดเดิมมาครอบ framework

## Stack ที่เลือกสำหรับ prototype

- WXT + TypeScript, Chrome Manifest V3
- React สำหรับ popup/status/pairing; ไม่ทำคิวหรือ business rules ใน popup
- Vitest กับ WXT test integration สำหรับ service worker/adapter contracts
- Python native host ขนาดเล็ก เชื่อมกับ FastAPI ที่รันในเครื่องลูกค้า
- FFmpeg/voice adapter อยู่ backend; Extension ไม่ render วิดีโอ

อ้างอิง: [WXT introduction](https://wxt.dev/guide/introduction.html),
[WXT unit testing](https://wxt.dev/guide/essentials/unit-testing)
Foundation ใช้ WXT 0.21.4 และล็อก dependencies แล้ว; popup/protocol/native host/pairing ทำแล้ว
content script, provider adapter, heartbeat และ dispatch ด้านล่างยังเป็นแผน

## Modules ที่เสนอ

| Module | หน้าที่ |
|---|---|
| entrypoints/background | handshake, reconnect, command validation และส่งต่อ events |
| entrypoints/chatgpt.content | ตรวจ DOM/ownership และเรียก adapter เฉพาะ document ที่กำหนด |
| entrypoints/popup | สถานะการจับคู่/เวอร์ชัน/ข้อผิดพลาดที่ผู้ใช้แก้ได้ |
| providers/chatgpt | preflight, submit, inspect, collect; selectors และ evidence แยกจาก transport |
| protocol | typed schemas, version compatibility และ bounded payloads |
| native host | Chrome framing, pairing credential และ authenticated backend bridge |

Backend เป็นเจ้าของ queue, lease, receipts, deadlines และ checkpoints ทั้งหมด
Service worker อาจถูกหยุด/เริ่มใหม่; ห้ามใช้ globals เป็นแหล่งความจริงของการส่ง
Reconnect ต้องอ่าน durable operation state แล้ว inspect ก่อนพิจารณาการส่งใหม่
อ้างอิง: [Chrome lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle)

## Transport และการจับคู่

**ทำแล้ว** ตามรายการนี้ใน [Extension foundation](../architecture/extension-foundation.md); ยกเว้น installer และ background heartbeat
ใช้ Chrome Native Messaging เป็น transport หลัก; E0 ต้องพิสูจน์ handshake/reconnect บน Windows ก่อนใช้จริง
Native host ส่งต่อเข้าช่อง API เฉพาะ browser agent บน loopback พร้อม credential ที่จำกัดสิทธิ์
จับคู่ผ่านหน้าจอแอปด้วย nonce อายุสั้น ใช้ครั้งเดียว และยืนยัน Extension ID ที่กำลังเชื่อม
Host เก็บ credential ด้วย Windows user protection; content script และหน้าเว็บไม่ได้รับ credential นี้
Backend revoke/rotate ได้; dev mode ไม่ยกเว้น pairing/auth; ห้ามใช้ owner token แทน
Native host manifest ต้องกำหนด allowed extension origins ที่แน่นอน; ตรวจ calling origin และ schema อีกชั้น
ลงทะเบียน host ใต้ HKCU ใน dev/setup และใน installer ลูกค้า; ไม่ต้องตั้ง server กลาง
Stdout ของ native host ใช้ protocol framing เท่านั้น; diagnostics เขียนไฟล์ที่กรองข้อมูลแล้ว
อ้างอิง: [Native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)

## Permissions และข้อจำกัด

- เริ่ม nativeMessaging/storage และ host access เฉพาะ ChatGPT ที่จำเป็นต่อ adapter
- เพิ่ม permission ทีละตัวตาม capability test; ไม่คัด debugger/downloads/clipboard หรือ provider อื่นมาทั้งชุด
- Media origins ต้อง allowlist ตามหลักฐานจริง; รับข้อมูลจากหน้าที่ผูกกับ operation เท่านั้น
- ตรวจ sender Extension ID/tab/document/frame/origin; ข้อมูลหน้าเว็บสั่ง privileged host โดยตรงไม่ได้
- ไม่ข้าม login, CAPTCHA, browser policy หรือข้อจำกัดบัญชี; แจ้ง USER_ACTION_REQUIRED พร้อม checkpoint
- DOM automation ต้องมี live pilot; fixture ผ่านไม่ได้รับรองว่าหน้า ChatGPT ปัจจุบันรองรับทุกขั้น
- ไม่รับรองการทำงานไร้คนดูแล 100%; ออกแบบให้ AI ตรวจ log/DB และแยกเหตุที่กู้เองได้กับเหตุที่ต้องให้ผู้ใช้ทำ

## การติดตั้งและส่งมอบ

แยก Extension identity, native host name และ dev profile จากระบบเก่า; ห้ามเปลี่ยนของเดิมเงียบ ๆ
รุ่นส่งมอบต้องมี app/helper/Extension protocol compatibility และตรวจเวอร์ชันที่ activate จริง
installer ต้องตรวจ host registration, launch และ handshake บน clean Windows ก่อนเรียกว่า client-ready
รายละเอียด message/receipt: [Protocol](extension-protocol.md); หลักฐานที่ต้องมี: [Testing](story-testing.md)
