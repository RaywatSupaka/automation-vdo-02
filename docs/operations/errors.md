# Errors and exceptions

เจ้าของ catalog คือ [errors.py](../../backend/smartflow/errors.py) และ API `GET /api/errors`
ไม่คัดลอกรายการทุก code ลงหลายเอกสาร; เปิด catalog เมื่อต้องเพิ่มหรือแก้ error จริง

## Contract ที่มีอยู่

`AppError` ระบุ code คงที่ และ `ErrorSpec` ระบุข้อความ recovery กับ HTTP status
Error payload มี `code`, `message`, `recovery`, `http_status`, `trace_id`, `stage`
Stage ใน generic HTTP errors อาจเป็น null; job diagnostic มี stage ของงานที่บันทึกไว้
Validation response ระบุ field และชนิดปัญหาโดยไม่ echo input ส่วนตัว

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

งานเพิ่ม typed response/error contract และ correlation ข้ามคำสั่งอยู่ใน
[Foundation plan](../planning/foundation.md); ยังไม่ถือว่าทำครบแล้ว

เทส: [test_contracts.py](../../tests/test_contracts.py), [test_api.py](../../tests/test_api.py),
[test_workflow.py](../../tests/test_workflow.py)
การอ่านหลักฐาน: [Diagnostics](diagnostics.md)
