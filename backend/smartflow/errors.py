from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ErrorSpec:
    message: str
    recovery: str
    http_status: int = 409


ERRORS = {
    "INPUT_INVALID": ErrorSpec("ข้อมูลไม่ถูกต้อง", "correct_input", 422),
    "UNAUTHORIZED": ErrorSpec("ต้องเชื่อมต่อด้วยสิทธิ์ของโปรแกรมนี้", "authenticate", 401),
    "ORIGIN_REJECTED": ErrorSpec("ไม่อนุญาตคำขอจากหน้าต่างนี้", "check_client", 403),
    "JOB_NOT_FOUND": ErrorSpec("ไม่พบงาน", "check_job_id", 404),
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
