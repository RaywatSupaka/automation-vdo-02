# Local API and data isolation

## Session boundary

- Bind API ที่ 127.0.0.1 เท่านั้น
- ทุก `/api` route ต้องมี session Bearer token รวม OpenAPI, logs และ DB diagnostics
- ตรวจ Origin; Dev อนุญาต Vite origin ที่กำหนดไว้ใน source เพิ่มจาก local API origin
- Desktop สร้าง token เฉพาะ session แล้วส่งผ่าน URL fragment
- UI ย้าย token ไป sessionStorage และลบ fragment ออกจาก address
- HTTP logs ไม่บันทึก URL/query/input/header values
- Credential ของ provider จริงยังไม่ได้ implement; ต้องออกแบบก่อนเพิ่ม adapter

## Inspection boundary

DB HTTP API เปิดเฉพาะตารางและ columns ที่กำหนด ไม่รับ SQL อิสระ
ข้อมูล private ของงานใช้เฉพาะ authenticated app; support export ใช้ allowlist แยก
กติกา log และเนื้อหา export อยู่ใน [Diagnostics](diagnostics.md)
ห้ามใช้ Dev/Test เพื่อแก้หรือล้างข้อมูลงานจริง

ยังไม่มีบริการอัปโหลด, cloud backend หรือ remote support
การติดตั้งโปรแกรมหรือส่ง ZIP ไม่ได้ให้สิทธิ์ AI เข้าถึงเครื่องลูกค้า
ถ้าจะเพิ่ม remote support ต้องระบุการอนุญาต ขอบเขต และการยกเลิกสิทธิ์แยกต่างหาก

Source: [api.py](../../backend/smartflow/api.py), [api.ts](../../frontend/src/api.ts),
[runtime.py](../../backend/smartflow/runtime.py)
เทส: [test_api.py](../../tests/test_api.py) / scope `api`
