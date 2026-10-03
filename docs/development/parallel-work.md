# Parallel sessions

กติกาเมื่อมีหลาย session หรือหลาย agent ทำงานในโปรเจกต์นี้พร้อมกัน
ใช้เพื่อไม่ให้แก้ทับงานกัน ไม่ให้ไฟล์ generate ปนงานที่ยังไม่ commit และไม่ให้ DB จริงถูก migrate โดยไม่ตั้งใจ

## แยกพื้นที่ทำงาน

- งานที่ใช้เวลานานหรือแก้หลายระบบ ให้ใช้ `git worktree` หรือ branch แยกต่อ session
- ถ้าต้องใช้ working tree เดียวกัน ให้ประกาศไฟล์ที่ตัวเองเป็นเจ้าของก่อนเริ่ม และแก้เฉพาะไฟล์ชุดนั้น
- ก่อนแก้แต่ละไฟล์ให้รัน `git status --short -- <file>`
  ถ้าไฟล์มีการแก้ที่ไม่ใช่ของเรา ให้หยุดแก้ไฟล์นั้นและรายงานเป็นงานที่ติดขัด
- ห้ามใช้ `git checkout`, `reset`, `stash`, formatter ทั้ง repo หรือ regenerate ไฟล์ที่มีงานของคนอื่นปนอยู่
- ถ้าเทสล้มในไฟล์ที่ไม่ได้แก้ ให้แยกรายงานว่าเกิดจากงานที่ยังไม่ commit ของอีก session ไม่ต้องแก้แทน

## ไฟล์ที่ generate และไฟล์ส่วนกลาง

- `contracts/openapi.json`: regenerate ด้วย `tools/export_contract.py` เฉพาะเมื่อ route ทุกตัวที่เปลี่ยนใน tree
  เป็นงานชุดเดียวกัน
  ถ้ามี route ของอีก session ปนอยู่ ให้แก้เฉพาะ schema ของงานเรา แล้วให้คนที่ commit ทีหลัง regenerate อีกครั้ง
- `tools/check_selection.py`, `docs/index.md` และ `docs/delivery/status.md` เป็นไฟล์ที่แก้ร่วมกันบ่อย
  ให้แก้ทีละบรรทัดที่ต้องการ อย่าเขียนทับทั้งไฟล์
- เทสไฟล์ใหม่ที่ยังเพิ่ม mapping ไม่ได้ เพราะไฟล์ selector ถูกแก้อยู่ ให้บันทึกเป็นงานค้างไว้
  ตอนนี้ selector จะเลือก `all` ให้เองจนกว่าจะเพิ่ม mapping

## Migration ที่ยังไม่ commit

`migrate()` อัปเกรดไป Alembic head ทุกครั้งที่ desktop หรือ API เริ่มทำงาน
([migration_safety.py](../../backend/smartflow/migration_safety.py))
ไฟล์ใน `migrations/versions/` ที่ยังไม่ commit จึงถูก apply ทันทีที่เปิดโปรแกรม

- ห้ามเปิด Dev desktop หรือ API ด้วยข้อมูลจริงใน `.smartflow/` ขณะมี migration ที่ยังไม่ commit
- ให้ตั้ง `SMARTFLOW_DATA_DIR` ไปยังโฟลเดอร์ sandbox ก่อนเปิด ([Setup](setup.md))
- Migration ใหม่ที่ downgrade ไม่ได้ ถ้าถูก apply กับ DB จริงแล้วต่อมาทิ้งไฟล์ migration ไป
  โปรแกรมจะเปิดไม่ขึ้นเพราะไม่รู้จัก revision นั้น
  ทางกลับมีทางเดียวคือ restore จาก `backups/before-<rev>-*.sqlite3`
- ถ้าเหตุนี้ทำให้ปิดเปิดโปรแกรมหลังแก้ UI ไม่ได้ ให้รายงานว่ายังค้าง
  ระบุ revision ที่ทำให้ติด และ build ที่รอเปิดใช้งาน
- Claude Code บังคับกติกานี้ด้วย hook ใน [.claude/settings.json](../../.claude/settings.json)
  ([guard_dev_start.py](../../.claude/hooks/guard_dev_start.py))
  hook จะปฏิเสธคำสั่ง Bash/PowerShell ที่เรียก `RUN_DEV.vbs`, `RUN_DEV.bat`, `desktop_entry.py`
  หรือ `smartflow.cli desktop|serve|api` เมื่อ `git status` พบไฟล์ `.py` ที่ยังไม่ commit ใน `migrations/versions/`
  ผ่านได้เมื่อคำสั่งตั้ง `SMARTFLOW_DATA_DIR`
  หรือ `SMARTFLOW_ALLOW_PENDING_MIGRATION=1` (ใช้ได้เฉพาะเมื่อเจ้าของโปรเจกต์อนุญาตชัดเจน)
  hook กันได้เฉพาะคำสั่งที่ agent รัน ไม่ได้กันการดับเบิลคลิกเปิดโปรแกรมเอง

## ส่งต่องาน

- ปัญหาที่พบในไฟล์ของอีก session ให้ส่งเป็นรายการ: ไฟล์, พฤติกรรมที่ผิด, เคสที่ทำให้เกิด และวิธีแก้ที่แนะนำ
  อย่าเข้าไปแก้เอง
- ถ้า commit งานของแต่ละ session ให้แยก commit ตามงาน และระบุผลเทสของงานนั้น
- หลังอีก session commit แล้ว ให้ตรวจ `git diff` ว่างานของเราไม่ถูกเขียนทับ แล้วค่อยรันเทสที่ได้รับผลอีกครั้ง

Source: [migration_safety.py](../../backend/smartflow/migration_safety.py), [check_selection.py](../../tools/check_selection.py),
[export_contract.py](../../tools/export_contract.py)
การเลือกเทส: [Test selection](test-selection.md)
