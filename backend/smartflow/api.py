import secrets
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from smartflow import __version__
from smartflow.config import Settings
from smartflow.db import Database
from smartflow.diagnostics import database_overview, job_diagnostic, overview, support_bundle, table_rows
from smartflow.engine import Engine
from smartflow.errors import ERRORS, AppError, error_payload
from smartflow.jobs import CreateJob, Jobs
from smartflow.observability import create_logger, emit, safe_exception
from smartflow.providers import Simulator


def web_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "web"
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()
    if len(settings.token) < 24:
        raise ValueError("Set SMARTFLOW_API_TOKEN with at least 24 characters")
    logger = create_logger(settings.data_dir)
    db = Database(settings.db_path, logger)

    @asynccontextmanager
    async def lifespan(app):
        db.migrate()
        emit(logger, "api.started", version=__version__)
        yield
        db.close()

    auth = HTTPBearer(auto_error=False)

    def authorized(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(auth)]):
        if not credentials or not secrets.compare_digest(credentials.credentials, settings.token):
            raise AppError("UNAUTHORIZED")

    app = FastAPI(
        title="SmartFlow Next",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.db = db
    jobs = Jobs(db)
    engine = Engine(db, Simulator(db), settings.data_dir)

    def failure(code, trace_id, status=None):
        return JSONResponse(
            {"error": error_payload(code, trace_id)}, status_code=status or ERRORS[code].http_status
        )

    @app.middleware("http")
    async def trace_and_origin(request: Request, call_next):
        request.state.trace_id = str(uuid4())
        start = time.perf_counter()
        allowed = {f"http://127.0.0.1:{settings.port}", f"http://localhost:{settings.port}"}
        if settings.mode == "dev":
            allowed.update({"http://localhost:5173", "http://127.0.0.1:5173"})
        origin = request.headers.get("origin")
        if request.url.path.startswith("/api") and origin and origin not in allowed:
            response = failure("ORIGIN_REJECTED", request.state.trace_id)
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                emit(logger, "api.exception", trace_id=request.state.trace_id, **safe_exception(exc))
                response = failure("INTERNAL_ERROR", request.state.trace_id)
        response.headers["X-Trace-ID"] = request.state.trace_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        route = getattr(request.scope.get("route"), "path", "unmatched")
        emit(
            logger,
            "api.request",
            trace_id=request.state.trace_id,
            method=request.method,
            route=route,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        return response

    @app.exception_handler(AppError)
    async def domain_error(request, exc):
        return failure(exc.code, request.state.trace_id)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic errors may contain user input. Only field location and type are safe.
        response = failure("INPUT_INVALID", request.state.trace_id)
        fields = [{"field": ".".join(str(p) for p in e["loc"]), "type": e["type"]} for e in exc.errors()]
        return JSONResponse(
            {"error": error_payload("INPUT_INVALID", request.state.trace_id), "fields": fields},
            status_code=response.status_code,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return failure("INPUT_INVALID", request.state.trace_id, exc.status_code)

    from fastapi import APIRouter

    router = APIRouter(prefix="/api", dependencies=[Depends(authorized)])

    @router.get("/health")
    def health():
        return {
            **overview(db),
            "mode": settings.mode,
            "worker_alive": getattr(app.state, "worker_alive", lambda: False)(),
        }

    @router.get("/openapi.json")
    def openapi():
        return app.openapi()

    @router.get("/errors")
    def errors():
        return {code: error_payload(code, "") for code in ERRORS}

    @router.post("/jobs", status_code=201)
    def create(
        data: CreateJob,
        request: Request,
        idempotency_key: Annotated[str, Header(min_length=8, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")],
    ):
        return jobs.create(data, idempotency_key, request.state.trace_id)

    @router.get("/jobs")
    def list_jobs(limit: Annotated[int, Query(ge=1, le=200)] = 100):
        return jobs.list(limit)

    @router.get("/jobs/{job_id}")
    def get_job(job_id: str):
        return jobs.get(job_id)

    @router.get("/jobs/{job_id}/events")
    def events(
        job_id: str, after: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=500)] = 200
    ):
        return jobs.events(job_id, after, limit)

    @router.post("/jobs/{job_id}/commands/{action}")
    def command(job_id: str, action: Literal["resume", "cancel", "reconcile"]):
        if action == "reconcile":
            engine.reconcile(job_id)
            return jobs.get(job_id)
        return jobs.command(job_id, action)

    @router.get("/jobs/{job_id}/diagnostics")
    def diagnostic(job_id: str):
        return job_diagnostic(db, job_id)

    @router.get("/jobs/{job_id}/support-bundle")
    def bundle(job_id: str):
        return Response(
            support_bundle(db, job_id),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="smartflow-support.zip"'},
        )

    @router.get("/diagnostics/database")
    def database():
        return database_overview(db)

    @router.get("/diagnostics/logs")
    def logs(limit: Annotated[int, Query(ge=1, le=200)] = 50):
        import json
        from collections import deque

        result = []
        for name in ("runtime.jsonl", "worker.jsonl"):
            path = settings.data_dir / "logs" / name
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as handle:
                lines = deque(handle, maxlen=limit)
            for line in lines:
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # A concurrent final line is retried on the next read.
        return sorted(result, key=lambda row: row["at"])[-limit:]

    @router.get("/diagnostics/database/{table}")
    def rows(table: Literal["jobs", "receipts", "events"], limit: Annotated[int, Query(ge=1, le=200)] = 50):
        return table_rows(db, table, limit)

    app.include_router(router)
    root = web_root()
    if (root / "assets").exists():
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        if (root / "index.html").exists():
            return FileResponse(root / "index.html")
        return JSONResponse({"app": "SmartFlow Next", "message": "Build frontend with npm run build"})

    return app
