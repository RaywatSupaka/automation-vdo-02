# Runtime boundaries

```text
React + TypeScript
        | authenticated loopback HTTP
FastAPI -------- diagnostics
        | commands / read models
Jobs service --- SQLite
                    |
Worker process --- Engine
                    |
               Provider protocol
                    |
               Simulator (0.1.0)
```

Desktop host ใช้ pywebview/WebView2 แสดง frontend ที่ build แล้ว และดูแล API/worker lifetime
UI ไม่เขียน DB โดยตรงและไม่ตัดสินใจส่งคำขอผู้ให้บริการซ้ำ
Backend และ worker อยู่เครื่องลูกค้า; ยังไม่มี cloud backend หรือ remote support

| หน้าที่ | Source |
|---|---|
| UI และ navigation | [App.tsx](../../frontend/src/App.tsx) |
| คำสั่ง API และ CLI | [api.py](../../backend/smartflow/api.py), [cli.py](../../backend/smartflow/cli.py) |
| สร้างงานและคำสั่งจากผู้ใช้ | [jobs.py](../../backend/smartflow/jobs.py) |
| เดินขั้นตอนงาน | [engine.py](../../backend/smartflow/engine.py) |
| ตัวประมวลผลและ desktop host | [worker.py](../../backend/smartflow/worker.py), [runtime.py](../../backend/smartflow/runtime.py) |

## Process ownership

Application lock และ worker lock แยกตาม data directory
Supervisor เริ่ม worker ใหม่ได้ไม่เกิน 3 ครั้งต่อ host session; เมื่อเกินบันทึก `WORKER_UNAVAILABLE`
Worker แต่ละตัวใช้ shutdown pipe ของตัวเองและ local Event
ไม่แชร์ synchronization lock กับ child ที่อาจถูก kill เพราะ lock อาจค้างหลัง process หาย
เมื่อ parent หาย worker จะหยุด; ข้อมูลค้างกู้ตาม receipt ที่บันทึกไว้

`worker_alive` ปัจจุบันหมายถึง process ยังอยู่ ไม่ยืนยัน readiness หรือความคืบหน้าของงาน
แผนเพิ่ม heartbeat/stall detection อยู่ใน [foundation plan](../planning/foundation.md)

เทส: [test_runtime.py](../../tests/test_runtime.py) / scope `runtime`
รายละเอียดสถานะงาน: [Automation](automation.md)
