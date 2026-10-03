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

Health แยกสัญญาณ: `worker_alive` = process ยังอยู่, `worker_state` = ความคืบหน้าของ loop จาก heartbeat
Worker เขียน `worker.heartbeat` (pid + เวลา) ทุกรอบ loop ไม่เกินวินาทีละครั้ง แบบ atomic replace
`ready` เมื่อ beat ของ pid ปัจจุบันไม่เกิน 5 วินาที, `late` เมื่อเกิน, `stalled` เมื่อไม่มี beat 30 วินาที
Supervisor บันทึก `WORKER_STALLED` แล้ว terminate และเริ่มใหม่ภายในโควตา 3 ครั้งเดิม; recovery อ่าน receipt ไม่ส่งซ้ำ
งานดูแล Story (`maintain`) ที่ล้มถูกบันทึก `STORY_MAINTENANCE_FAILED` และลองใหม่แบบ backoff 2–30 วินาที ไม่ทำให้ worker ตาย
ยังไม่มี end-to-end test ที่ supervisor ฆ่า worker ที่ค้างจริง (ต้องรอ 30 วินาที); ตรวจด้วย unit test ของการตัดสินสถานะ
Source: [heartbeat.py](../../backend/smartflow/heartbeat.py)

เทส: [test_runtime.py](../../tests/test_runtime.py) / scope `runtime`
รายละเอียดสถานะงาน: [Automation](automation.md)
