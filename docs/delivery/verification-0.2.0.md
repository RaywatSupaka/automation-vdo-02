# Portable 0.2.0 verification — 2026-10-03

## Scope and source

F5a T0–T6 บน `dev` เริ่มจาก `ae0ecbc` (working tree ว่าง) ชุดเก่า 0.1.0 จาก `5847f79`
ถูกคัดลอกไป `build/previous-package/SmartFlow Next 0.1.0` เพื่อทดสอบอัปเกรด (0.458 s)
ชุด portable 0.2.0 build จาก commit `cd8ab08ca47ce5152212c7065ba1c214e4f864a0` ที่ commit แล้ว;
`source_dirty=false` สคริปต์ smoke/เอกสารที่ commit ภายหลังไม่ได้เปลี่ยนไฟล์ในชุด

| งาน | Commit | ผล |
|---|---|---|
| T1 | `e746366` | app/package/API version 0.2.0, UI รอ health แล้วจึงแสดงเวอร์ชัน |
| T2 | `cd8ab08` | รวม native helper และ Extension ใน portable; manifest ตรวจเวอร์ชันและ hash |
| T3 | `f34a8cc` | packaged smoke แยก prod/test และตรวจ draft/Story `SIMULATION` |
| T4 | `47bca9a` | upgrade smoke จากชุด 0.1.0 บนข้อมูลชั่วคราว |
| T5 | `349590b` | pairing smoke ใช้ helper จาก portable ผ่าน Chromium profile แยก |
| T6 | ดู `git log -1 -- docs/delivery/verification-0.2.0.md` | เอกสารส่งมอบและข้อจำกัด |

## Build manifest

`dist/SmartFlow Next/build-manifest.json` หลัง build; ไม่มี path หรือข้อมูลส่วนตัว:

```json
{
  "version": "0.2.0",
  "app_version": "0.2.0",
  "helper_version": "0.2.0",
  "extension_version": "0.2.0",
  "extension_manifest_version": "0.2.0",
  "source_commit": "cd8ab08ca47ce5152212c7065ba1c214e4f864a0",
  "source_dirty": false,
  "built_at": "2026-10-03T09:21:51.029684+00:00",
  "provider": "simulator",
  "exe_sha256": "ca48587777c6d145dc30d8031f38bc418ee0022075580f0122886357f6b87950",
  "helper_sha256": "e41c5b31e5f8446790a6b1c30fd17cf1e8662a0e326b75c5413c883ace79ccd3",
  "clean_machine_verified": false
}
```

ตรวจ `SmartFlow Next.exe` และ `helper/SmartFlowNextHost.exe` ด้วย SHA-256 เทียบ manifest แล้วตรงทั้งคู่;
`extension/chrome-mv3/manifest.json` มีอยู่ในชุด

## Checks actually run

| Command | Result | Measured seconds |
|---|---|---:|
| `tools/check.py --scope unit api-core ui typecheck` ก่อน T1 | backend 86, UI 96, typecheck ผ่าน | lint 3.334; backend 10.967; UI 1.967; typecheck 40.216 |
| `tools/check.py --scope api-core --match test_health_reports_release_version` ก่อน/หลัง T1 | 0.1.0 แทน 0.2.0 ก่อนแก้; ผ่านหลังแก้ | 2.856 / 2.752 |
| `tools/check.py --scope api-core --match test_all_json_response_contracts_and_saved_openapi` หลังอัปเดต OpenAPI | 1 ผ่าน | 3.572 |
| `tools/check.py --scope unit api-core ui typecheck` T1 | backend 87, UI 96, typecheck ผ่าน | lint 0.341; backend 19.444; UI 7.195; typecheck 11.868 |
| `tools/check.py --scope tooling` ก่อน/หลัง T2 | 45 / 53 ผ่าน | 1.542 / 1.572 |
| `tools/check.py --scope tooling --match test_build_manifest_contains_versions_and_executable_hashes` ก่อน T2 | ไม่มี manifest builder ตามสัญญา | 0.757 |
| `tools/build.py` หลัง commit T2 | ผ่าน; `source_dirty=false` | 167.917 |
| `tools/packaged_smoke.py` ก่อน/หลัง T3 | prod `unknown_send` ได้ 409 ก่อนแก้; ทุก key ผ่านหลังแก้ ยกเว้น clean_machine=false | 4.426 / 32.258 |
| `tools/upgrade_smoke.py` T4 | 0001 → 0004; backup integrity ok; งานเดิมยังอ่านได้ | 7.832 |
| `tools/pairing_smoke.py --story --helper "dist/SmartFlow Next/helper"` ก่อน/หลัง T5 | option ยังไม่มี ก่อนแก้; pairing/Story ผ่านหลังแก้ | 1.199 / 21.846 |
| `tools/check.py --scope all` หลัง T5, ครั้งเดียว | lint, backend 255, UI 96, E2E 12, Extension unit 13, builds/typechecks/smoke ผ่าน | 216.883 รวมเวลารายขั้น |

`--scope all` รายขั้น: lint 0.283 s; backend 81.388 s; UI 3.998 s; UI build 9.267 s;
E2E 43.831 s; Extension unit 52.280 s; Extension typecheck 17.954 s;
Extension build 3.331 s; Extension smoke 4.551 s

## Evidence by layer

- **Unit/E2E:** Backend 255, UI 96, E2E 12 และ Extension unit 13 ผ่านใน final gate; build/typecheck ผ่าน
- **Portable EXE:** packaged smoke ใช้ data dir แยก prod/test ตรวจ health 0.2.0 และ worker ready,
  prod success และ fault scenario denial, draft POST/PATCH/restore หลัง restart, Story `SIMULATION`
  ผ่าน agent API พร้อม artifact checksum ตรง receipt และ diagnostics ไม่เผยหัวข้อ;
  test mode ยืนยัน unknown send ไม่ส่งซ้ำและ save recovery; native WebView smoke ผ่าน
- **Upgrade:** EXE 0.1.0 สร้างงาน success บน schema 0001; EXE 0.2.0 เปิด data dir เดิมแล้วได้ schema 0004,
  `before-0001-*.sqlite3` ตรวจ integrity `ok`, งานเดิมยัง completed และ worker ready
- **Dev desktop activation:** ปิด PID 42752 ด้วย `CloseMainWindow()` และไม่พบ process หลัง 20 วินาที;
  เปิด `RUN_DEV.vbs` เดิมแล้วได้หน้าต่าง PID 30992 ภายใน 40 วินาที หน้า local เสิร์ฟ
  `assets/index-BR1C9_Fp.js` ตรงกับ UI build; ยังไม่ได้ตรวจตัวอักษรเวอร์ชันในหน้าต่างด้วย native UI
- **Chromium profile แยก:** packaged helper ผ่าน native pairing, credential ข้าม helper process,
  revocation และ Story runner จำลอง; registry key `com.smartflow.next.smoke_*` เหลือ 0
- **Real Chrome ของเจ้าของ:** ไม่ได้ติดตั้งหรือเปิด Extension จากชุด portable ใน profile เจ้าของ
- **Clean Windows / installed package / provider จริง:** ไม่ได้ตรวจ; `clean_machine_verified=false`

ไม่อยู่ใน F5a: installer, signing, WebView2 บน clean Windows, นโยบายข้อมูลตอนถอนติดตั้ง,
การลงทะเบียน helper ของชุดในเครื่องลูกค้า และ provider ที่สร้างสื่อจริง
