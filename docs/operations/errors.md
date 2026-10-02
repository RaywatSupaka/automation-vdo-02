# Errors and exceptions

เจ้าของ catalog คือ [errors.py](../../backend/smartflow/errors.py) และ API `GET /api/errors`
ไม่คัดลอกรายการทุก code ลงหลายเอกสาร; เปิด catalog เมื่อต้องเพิ่มหรือแก้ error จริง

## Contract ที่มีอยู่

`AppError` ระบุ code คงที่ และ `ErrorSpec` ระบุข้อความ recovery กับ HTTP status
Error payload มี `code`, `message`, `recovery`, `http_status`, `trace_id`, `stage`
Stage ใน generic HTTP errors อาจเป็น null; job diagnostic มี stage ของงานที่บันทึกไว้
Validation response ระบุ field และชนิดปัญหาโดยไม่ echo input ส่วนตัว
ชื่อ extra field ที่ผู้ใช้ส่งมาถูกแทนด้วย `unknown` เพื่อไม่ให้ชื่อ field กลายเป็นช่องรั่วของข้อมูล
HTTP status ตรงกับ `error.http_status`; response และ error ใช้ request trace เดียวกัน
Route ที่ไม่มีใช้ `ROUTE_NOT_FOUND` (404); method ผิดใช้ `METHOD_NOT_ALLOWED` (405) พร้อม Allow header
Job ไม่พบใช้ `JOB_NOT_FOUND` (404); input ผิด 422, domain conflict 409, unexpected exception 500
คำสั่งบนงานที่พบแล้วแนบ stage ของงานขณะรับคำสั่ง; trace ประจำงานยังอยู่ใน job/events

| ตัวอย่าง | สิ่งที่หลักฐานบอก | แนวทาง |
|---|---|---|
| INPUT_INVALID | input ไม่ผ่าน schema | แก้ข้อมูลก่อนเริ่ม |
| PROVIDER_AUTH_REQUIRED | preflight ต้องการ login | พักให้ผู้ใช้ดำเนินการ |
| SEND_ACCEPTANCE_UNKNOWN | ยังยืนยันการรับคำขอไม่ได้ | inspect คำขอเดิม ห้าม replay |
| MEDIA_SAVE_FAILED | เก็บผลไว้แล้ว แต่บันทึกไฟล์ไม่ได้ | retry เฉพาะการบันทึก |
| WORKER_UNAVAILABLE | supervisor ใช้ restart budget หมด | ตรวจ worker log |
| INTERNAL_ERROR | ยังไม่ได้จำแนกข้อผิดพลาดนี้ | ใช้ trace และ stack frames ตรวจต้นเหตุ |

## กติกาการเพิ่ม error

- แยกเหตุจากสิ่งที่สังเกตได้ เช่น ยังไม่ส่ง / ส่งไม่แน่ใจ / ได้ผลแล้วแต่ save ไม่สำเร็จ
- ระบุว่าการ retry ปลอดภัยหรือไม่และต้องใช้ checkpoint ใด
- ไม่ catch แล้วเงียบ หรือสรุปเป็น network/provider failure โดยไม่มีหลักฐาน
- ข้อความสำหรับผู้ใช้แก้ได้ แต่ code และความหมายต้องคงที่หรือมี migration ของ contract
- ข้อผิดพลาดหลัง dispatch ต้องรักษาความไม่แน่ใจและห้าม replay
- ทดสอบเหตุจริงและเคสสำคัญเรื่องเวลา/คำสั่งซ้ำก่อนเปิดใช้

Typed response/error contract และ correlation ข้ามคำสั่งทำแล้วใน F1
ดู [API](api.md) และ [หลักฐาน F1](../delivery/verification-f1.md)

เทส: [test_contracts.py](../../tests/test_contracts.py), [test_api.py](../../tests/test_api.py),
[test_workflow.py](../../tests/test_workflow.py)
การอ่านหลักฐาน: [Diagnostics](diagnostics.md)
