# Provider adapters

**ทำแล้ว:** Provider protocol และ offline Simulator
**ยังไม่ทำ:** ChatGPT, Gemini, Flow, Meta, Chrome Extension และ real media rendering

Source: [providers.py](../../backend/smartflow/providers.py)

## Boundary

| Operation | หน้าที่ |
|---|---|
| preflight | ตรวจเงื่อนไขก่อนการส่ง ยังไม่มี side effect ของ submit |
| submit | ส่งคำขอที่มี durable request ID และเจ้าของแน่นอน |
| inspect | อ่านผลของคำขอเดิม โดยไม่ submit ใหม่ |

กติกา receipt และ retry อยู่ใน [Automation](automation.md); ห้ามแก้ผ่อนคลายใน adapter
ผู้ให้บริการจริงต้องมี timeout ต่อ operation, cancellation และ acceptance evidence
แยก credentials/profile ตามเจ้าของงาน และไม่บันทึกลง logs หรือ support exports

## เกณฑ์ก่อนเปิดใช้ provider จริง

1. มี typed contract, error mapping และ fixture ของคำตอบ/ข้อผิดพลาด
2. ตรวจ login, tab/document/request ownership และ version compatibility ตามช่องทางที่ใช้
3. เคส crash/คำตอบช้า/คำสั่งซ้ำ/ผลส่งไม่แน่ใจต้องไม่สร้างงานซ้ำ
4. มี read-only reconciliation และเหตุผลที่ตรวจย้อนกลับได้
5. ตรวจ source fixture, แพ็กที่เปิดใช้ และ provider output จริงแยกกัน

เริ่ม provider pilot หนึ่งรายกับงานหนึ่งขั้นตอนหลัง infrastructure gates ผ่าน
ไม่เปิดทั้ง Story/Product/Drama พร้อมกัน และไม่เรียกสื่อจำลองว่าเป็นผลจริง
Simulator ต้องยังใช้ได้ใน normal tests เพื่อคุมเวลาและค่าใช้จ่าย

เทสต้นแบบ: [test_workflow.py](../../tests/test_workflow.py)
เกณฑ์จัดลำดับงาน: [Foundation plan](../planning/foundation.md)
แผน provider แรก (ยังไม่ implement): [Story Shorts](../planning/story-shorts.md)
ขอบเขต browser adapter ใหม่: [Extension design](../planning/browser-extension.md)
