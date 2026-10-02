export const statusLabels: Record<string, string> = {
  queued: 'รอทำงาน', running: 'กำลังทำงาน', waiting: 'รอลองใหม่', needs_review: 'ต้องตรวจสอบ',
  completed: 'สำเร็จ', failed: 'พบข้อผิดพลาด', cancelled: 'ยกเลิกแล้ว',
};

export function actions(status: string, receipt: string | undefined) {
  const uncertain = receipt === 'unknown' || receipt === 'dispatching';
  return {
    resume: ['failed', 'cancelled'].includes(status) && !uncertain,
    reconcile: ['needs_review', 'cancelled'].includes(status) && !!receipt,
    cancel: !['completed', 'cancelled'].includes(status),
  };
}
