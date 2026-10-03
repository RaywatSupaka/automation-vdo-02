from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ErrorSpec:
    message: str
    recovery: str
    http_status: int = 409


ERRORS = {
    "EXTENSION_STORAGE_FAILED": ErrorSpec("Extension storage failed", "inspect_extension_storage"),
    "ARTIFACT_WRITE_FAILED": ErrorSpec("Cannot persist the collected artifact", "retry_local_save"),
    "STORY_CAPABILITY_UNAVAILABLE": ErrorSpec("รอบนี้รองรับงานจำลองแบบคลิปเดียว", "select_single_simulation", 422),
    "STORY_DRAFT_INVALID": ErrorSpec("ระบุหัวข้อและตรวจค่าของแบบร่างก่อนเริ่ม", "correct_draft", 422),
    "STORY_RESULT_INVALID": ErrorSpec("ผลจำลองไม่ตรงกับคำขอของงานนี้", "inspect_existing_result", 422),
    "EXTENSION_DISCONNECTED": ErrorSpec("กำลังรอ Extension ที่จับคู่แล้วเชื่อมต่อ", "connect_paired_extension"),
    "BROWSER_CONNECTION_BUSY": ErrorSpec("มี browser session อื่นกำลังใช้การจับคู่นี้", "wait_for_previous_lease"),
    "BROWSER_RETRY_EXHAUSTED": ErrorSpec("ครบจำนวนครั้งหรือเวลารอ Extension", "inspect_and_resume"),
    "OPERATION_OWNERSHIP_MISMATCH": ErrorSpec("คำสั่งไม่ได้เป็นของ agent หรืองานนี้", "refresh_owned_operation", 403),
    "OPERATION_LEASE_EXPIRED": ErrorSpec("สิทธิ์ทำงานรอบนี้หมดอายุหรือถูกแทนที่", "reclaim_for_inspection"),
    "DRAFT_ASSET_INVALID": ErrorSpec("ไฟล์ไม่ถูกต้องหรือไม่ได้เป็นของแบบร่างนี้", "select_valid_file", 422),
    "DRAFT_ASSET_MISSING": ErrorSpec("ไฟล์ที่บันทึกไว้หายหรือเสียหาย", "replace_missing_file"),
    "DRAFT_ASSET_QUOTA": ErrorSpec("พื้นที่ไฟล์ของแบบร่างเต็ม", "use_new_draft"),
    "DRAFT_ASSET_BUSY": ErrorSpec("กำลังนำเข้าไฟล์เดียวกัน", "retry_same_import"),
    "DRAFT_SAVE_FAILED": ErrorSpec("บันทึกแบบร่างหรือไฟล์ไม่สำเร็จ", "retry_same_request", 500),
    "EXTENSION_ID_MISMATCH": ErrorSpec("Extension ID ไม่ตรงกับโปรแกรมรุ่นนี้", "use_matching_extension"),
    "EXTENSION_VERSION_MISMATCH": ErrorSpec("รุ่น Extension หรือ helper ไม่ตรงกัน", "update_extension"),
    "PAIRING_EXPIRED": ErrorSpec("รหัสจับคู่หมดอายุ", "create_new_pairing"),
    "PAIRING_ALREADY_USED": ErrorSpec("รหัสนี้ถูกใช้จับคู่แล้ว", "create_new_pairing"),
    "PAIRING_NOT_FOUND": ErrorSpec("ไม่พบการจับคู่", "refresh_pairings", 404),
    "DRAFT_NOT_FOUND": ErrorSpec("ไม่พบแบบร่างในพื้นที่ทำงานนี้", "check_draft_id", 404),
    "DRAFT_REVISION_CONFLICT": ErrorSpec("แบบร่างมีการแก้ไขจากอีกหน้าต่าง", "read_latest_before_save"),
    "DRAFT_ASSET_UNAVAILABLE": ErrorSpec("ยังไม่เปิดนำเข้าไฟล์แบบร่าง", "keep_local_files"),
    "DATABASE_UPGRADE_FAILED": ErrorSpec("อัปเกรดฐานข้อมูลไม่สำเร็จ เก็บข้อมูลเดิมไว้แล้ว", "inspect_trace", 500),
    "INPUT_INVALID": ErrorSpec("ข้อมูลไม่ถูกต้อง", "correct_input", 422),
    "UNAUTHORIZED": ErrorSpec("ต้องเชื่อมต่อด้วยสิทธิ์ของโปรแกรมนี้", "authenticate", 401),
    "PERMISSION_DENIED": ErrorSpec("session นี้ไม่มีสิทธิ์ทำรายการนี้", "request_permission", 403),
    "ORIGIN_REJECTED": ErrorSpec("ไม่อนุญาตคำขอจากหน้าต่างนี้", "check_client", 403),
    "JOB_NOT_FOUND": ErrorSpec("ไม่พบงาน", "check_job_id", 404),
    "ROUTE_NOT_FOUND": ErrorSpec("ไม่พบ API ที่เรียก", "check_route", 404),
    "METHOD_NOT_ALLOWED": ErrorSpec("API นี้ไม่รองรับวิธีเรียกที่ใช้", "check_method", 405),
    "INVALID_TRANSITION": ErrorSpec("สถานะงานยังไม่รองรับคำสั่งนี้", "inspect_job"),
    "IDEMPOTENCY_CONFLICT": ErrorSpec("รหัสคำสั่งนี้เคยใช้กับข้อมูลอื่น", "use_new_command"),
    "PROVIDER_AUTH_REQUIRED": ErrorSpec("ผู้ให้บริการต้องการการเข้าสู่ระบบ", "user_action"),
    "PROVIDER_UNAVAILABLE": ErrorSpec("ผู้ให้บริการยังไม่พร้อมก่อนเริ่มส่ง", "bounded_retry"),
    "SEND_ACCEPTANCE_UNKNOWN": ErrorSpec("ยังยืนยันไม่ได้ว่าผู้ให้บริการรับคำขอ", "inspect_existing_request"),
    "RESULT_PENDING": ErrorSpec("ยังไม่ได้ผลลัพธ์จากคำขอเดิม", "bounded_observation"),
    "MEDIA_SAVE_FAILED": ErrorSpec("ได้ผลลัพธ์แล้ว แต่บันทึกไฟล์ไม่สำเร็จ", "retry_save"),
    "WORKER_INTERRUPTED": ErrorSpec("ตัวประมวลผลหยุดก่อนจบขั้นตอน", "resume_checkpoint"),
    "WORKER_UNAVAILABLE": ErrorSpec("ตัวประมวลผลไม่พร้อมหลังพยายามกู้คืน", "inspect_worker_log", 503),
    "INTERNAL_ERROR": ErrorSpec("เกิดข้อผิดพลาดภายในโปรแกรม", "inspect_trace", 500),
}


class AppError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def error_payload(code: str, trace_id: str, stage: str | None = None):
    return {"code": code, **asdict(ERRORS[code]), "trace_id": trace_id, "stage": stage}
