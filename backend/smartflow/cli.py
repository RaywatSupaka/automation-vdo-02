import argparse
import json
import multiprocessing
import os
import secrets
import sys
from dataclasses import replace

from smartflow.config import Settings


def main():
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description="SmartFlow Next: desktop and inspectable local API")
    parser.add_argument(
        "command", choices=["desktop", "serve", "api", "doctor"], nargs="?", default="desktop"
    )
    parser.add_argument("--port", type=int)
    parser.add_argument("--no-worker", action="store_true")
    parser.add_argument("--desktop-smoke", action="store_true")
    parser.add_argument(
        "--offline", action="store_true", help="Read local diagnostics without starting the API"
    )
    parser.add_argument("--path", default="/api/health")
    parser.add_argument("--method", default="GET", choices=["GET", "POST"])
    parser.add_argument("--body", help="Path to a JSON request file")
    parser.add_argument("--key", help="Idempotency key for create requests")
    args = parser.parse_args()
    if getattr(sys, "frozen", False):
        os.environ.setdefault("SMARTFLOW_MODE", "prod")
    settings = Settings.from_env()
    if args.port:
        settings = replace(settings, port=args.port)
    if args.command in {"api", "doctor"}:
        if args.command == "doctor" and args.offline:
            from smartflow.offline import diagnose

            report = diagnose(settings)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["database"] == "ok" else 1
        import httpx

        if not settings.token:
            parser.error("Set SMARTFLOW_API_TOKEN to the running API session token")
        path = "/api/health" if args.command == "doctor" else args.path
        if not path.startswith("/api/") or "?" in path or "#" in path:
            parser.error("--path must be a local /api/ route without query or fragment")
        from pathlib import Path

        headers = {"Authorization": f"Bearer {settings.token}"}
        if args.key:
            headers["Idempotency-Key"] = args.key
        data = json.loads(Path(args.body).read_text(encoding="utf-8-sig")) if args.body else None
        response = httpx.request(
            args.method, f"http://127.0.0.1:{settings.port}{path}", headers=headers, json=data, timeout=10
        )
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        return 0 if response.is_success else 1
    if args.command == "desktop":
        from smartflow.runtime import desktop

        try:
            desktop(replace(settings, token=settings.token or secrets.token_urlsafe(32)), args.desktop_smoke)
        except Exception as exc:
            from smartflow.observability import create_logger, emit, safe_exception

            # pythonw and the packaged GUI have no stderr console. Keep a safe
            # diagnostic and show an actionable message instead of failing silently.
            try:
                emit(
                    create_logger(settings.data_dir),
                    "desktop.start_failed",
                    code="INTERNAL_ERROR",
                    **safe_exception(exc),
                )
            finally:
                if os.name == "nt" and not args.desktop_smoke:
                    import ctypes

                    ctypes.windll.user32.MessageBoxW(
                        None,
                        "เปิดโปรแกรมไม่สำเร็จ ตรวจว่าไม่ได้เปิดโปรแกรมซ้ำ "
                        "และใช้คำสั่ง doctor --offline เพื่อตรวจข้อมูลวิเคราะห์",
                        "SmartFlow Next",
                        0x10,
                    )
            return 1
        return 0
    if len(settings.token) < 24:
        parser.error("Set SMARTFLOW_API_TOKEN with at least 24 characters; never put it in Git or logs")
    import uvicorn

    from smartflow.runtime import runtime

    with runtime(settings, worker=not args.no_worker) as app:
        uvicorn.run(app, host="127.0.0.1", port=settings.port, access_log=False, log_config=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
