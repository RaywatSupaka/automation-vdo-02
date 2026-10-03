# Authentication, authorization and local data

API บนเครื่องลูกค้าต้องตรวจสิทธิ์ด้วย; การ bind loopback ไม่ได้ยืนยันตัวตนของผู้เรียก
แยกการยืนยัน session ออกจาก permission ของแต่ละคำสั่งตั้งแต่เริ่มเพิ่มฟีเจอร์
แนวทาง: [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)

## Session boundary

- Bind API ที่ 127.0.0.1 เท่านั้น
- ทุก `/api` route ต้องมี session Bearer token รวม OpenAPI, logs และ DB diagnostics
- Token หาย/ผิดคืน `UNAUTHORIZED` 401 พร้อม WWW-Authenticate: Bearer
- Token ถูกแต่ไม่มีสิทธิ์คืน `PERMISSION_DENIED` 403; ไม่เรียก business handler และไม่แก้ DB
- ตรวจ Origin; Dev อนุญาต Vite origin ที่กำหนดไว้ใน source เพิ่มจาก local API origin
- Desktop สร้าง token เฉพาะ session แล้วส่งผ่าน URL fragment
- Token ที่ desktop สุ่มใหม่เปลี่ยนเมื่อเปิดใหม่; token ที่กำหนดเองใน environment มีอายุเท่ากับ server session ที่ยอมรับค่านั้น และจะใช้ซ้ำเมื่อเริ่มด้วยค่าเดิม
- UI ย้าย token ไป sessionStorage และลบ fragment ออกจาก address
- HTTP logs ไม่บันทึก URL/query/input/header values
- Credential ของ provider จริงยังไม่ได้ implement; ต้องออกแบบก่อนเพิ่ม adapter

## Roles และ policy

`auth.py` เป็นเจ้าของ permissions; `GET /api/session` คืน actor/role/permissions/auth_mode โดยไม่มี token
OpenAPI ของทุก route ระบุ `x-required-permission`; FastAPI dependency ตรวจทุก request
Guard อยู่ระดับแอป จึงครอบคลุม API ที่เพิ่มนอก router เดิมด้วย; HTML shell/assets เป็น public
Route ที่ไม่ได้ระบุ permission ถูกปฏิเสธ แม้ถือ owner token; UI ซ่อนปุ่มตามสิทธิ์แต่ backend เป็นผู้ตัดสิน

| Role | สิทธิ์ |
|---|---|
| owner | จัดการงาน/diagnostics/draft และ browser:manage; ไม่ใช้ permission เฉพาะ agent/nonce |
| operator | อ่าน/สร้าง/สั่งงาน พร้อมดู session/schema; ไม่มี log/DB/export |
| viewer | อ่านงานและ session/schema; สั่งงานไม่ได้ |
| support | อ่าน diagnostics/DB projections/log และ export แบบกรองข้อมูล; อ่านเนื้อหางานหรือสั่งงานไม่ได้ |

Draft API เพิ่ม `stories:drafts:read` ให้ owner/operator/viewer และ `stories:drafts:write` ให้ owner/operator
Support อ่านเฉพาะ draft diagnostics ที่ไม่มี config
Extension ใช้ DPAPI-protected scoped credential; agent ได้เฉพาะ browser:status และ browser:work ไม่มี draft/job/diagnostics access
browser:work ใช้ได้กับ operation ที่ pairing นั้นถือ lease อยู่เท่านั้น; pairing ที่ถูก revoke ทำอะไรต่อไม่ได้
งานที่ส่งไม่แน่ใจของ pairing ที่ถูก revoke ถูกปล่อยให้ pairing ใหม่ inspect ได้ แต่ไม่ได้ grant ส่งซ้ำ
Pairing nonce/expiry/revoke และขอบเขต host: [Extension pairing](../architecture/extension-foundation.md)

`SMARTFLOW_SESSION_ROLE` กำหนด role ฝั่ง server ของ API token หลัก (default owner)
`SMARTFLOW_DIAGNOSTICS_TOKEN` เป็น token ทางเลือกสำหรับ support ต้องต่างจาก token หลักและยาวอย่างน้อย 24 ตัว
ให้สร้างด้วยตัวสุ่มที่ปลอดภัยและส่งผ่าน environment เฉพาะ process ที่ได้รับอนุญาต ห้ามบันทึกลงไฟล์หรือ Git
ไม่รับ role/permissions จาก header, query หรือ payload ของผู้เรียก
Log มี `auth.denied`, actor_id, role, trace และ error code โดยไม่เก็บ credential

## Dev bypass และการเปิดจริง

- `SMARTFLOW_AUTH_MODE=local_session` (default): ตัวตนของ local desktop session ไม่ใช่บัญชีออนไลน์
- `SMARTFLOW_AUTH_MODE=dev_bypass`: ใช้ development identity เพื่อยังไม่ต้องเชื่อมระบบบัญชี
- RUN_DEV.vbs เลือก dev_bypass เมื่อไม่ได้ระบุ mode; หน้าจอแสดงว่ากำลังใช้ตัวตนจำลอง
- ทั้งสอง mode ยังตรวจ Bearer token, Origin และ permissions; bypass ไม่เพิ่มสิทธิ์ให้ viewer/support
- dev_bypass ใช้เฉพาะ mode dev/test และห้ามใน frozen EXE ทุกกรณี แม้ตั้ง SMARTFLOW_MODE=dev
- Config mode/role ผิด, token สั้น หรือ support token ซ้ำ ทำให้เริ่มไม่ได้ก่อนเปิดฐานข้อมูล
- ยังไม่มี account login, OIDC, license, subscription, token refresh หรือการยืนยันผู้ใช้ Windows รายบุคคล

รุ่น local ใช้ workspace เดียวต่อ data directory; roles ไม่ใช่ระบบแบ่งเจ้าของงานระหว่างหลายลูกค้า
ถ้าจะทำหลายบัญชี ต้องเพิ่ม ownership ของข้อมูลและตรวจ object-level access ที่ service/query ด้วย
เจ้าของเครื่องที่แก้ source/process/DB ได้ยังแก้ระบบ local ได้; กติกานี้ไม่ใช่ DRM หรือการรับรอง license
ถ้าต้องมีบัญชี/สิทธิ์ซื้อจากส่วนกลาง ให้ต่อผู้ตรวจยืนยันที่ auth boundary และให้ server กลางเป็นแหล่งสิทธิ์
Backend ประมวลผลงานยังรันบนเครื่องลูกค้าได้ ไม่จำเป็นต้องย้ายตามระบบบัญชี

## Inspection boundary

DB HTTP API เปิดเฉพาะตารางและ columns ที่กำหนด ไม่รับ SQL อิสระ
ข้อมูล private ของงานใช้เฉพาะ authenticated app; support export ใช้ allowlist แยก
กติกา log และเนื้อหา export อยู่ใน [Diagnostics](diagnostics.md)
ห้ามใช้ Dev/Test เพื่อแก้หรือล้างข้อมูลงานจริง

ยังไม่มีบริการอัปโหลด, cloud backend หรือ remote support
การติดตั้งโปรแกรมหรือส่ง ZIP ไม่ได้ให้สิทธิ์ AI เข้าถึงเครื่องลูกค้า
ถ้าจะเพิ่ม remote support ต้องระบุการอนุญาต ขอบเขต และการยกเลิกสิทธิ์แยกต่างหาก

Source: [auth.py](../../backend/smartflow/auth.py), [api.py](../../backend/smartflow/api.py), [api.ts](../../frontend/src/api.ts),
[runtime.py](../../backend/smartflow/runtime.py)
เทส: [test_auth.py](../../tests/test_auth.py), [test_api.py](../../tests/test_api.py) / scope `api`
หลักฐาน: [Verification auth](../delivery/verification-auth.md)
