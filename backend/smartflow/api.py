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
from smartflow.auth import AccessControl, AuthMode, Permission, policy
from smartflow.config import Settings
from smartflow.contracts import (
    DatabaseResponse,
    DiagnosticResponse,
    ErrorInfo,
    EventResponse,
    EventRow,
    HealthResponse,
    JobResponse,
    JobRow,
    LogResponse,
    OpenAPIDocument,
    ReceiptRow,
    SessionResponse,
    error_responses,
)
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
    access = AccessControl(settings)
    logger = create_logger(settings.data_dir)
    db = Database(settings.db_path, logger)

    @asynccontextmanager
    async def lifespan(app):
        db.migrate()
        emit(logger, "api.started", version=__version__)
        if access.mode == AuthMode.DEV_BYPASS:
            emit(logger, "auth.development_identity", auth_mode=access.mode.value, role=access.role.value)
        yield
        db.close()

    auth = HTTPBearer(auto_error=False)

    def authorized(
        request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(auth)]
    ):
        if request.url.path != "/api" and not request.url.path.startswith("/api/"):
            return  # Public desktop shell/assets contain no user data.
        try:
            principal = access.authenticate(credentials.credentials if credentials else None)
            request.state.principal = principal
            required = (getattr(request.scope.get("route"), "openapi_extra", None) or {}).get(
                "x-required-permission"
            )
            access.require(principal, required)
        except AppError as exc:
            principal = getattr(request.state, "principal", None)
            emit(
                logger,
                "auth.denied",
                trace_id=request.state.trace_id,
                code=exc.code,
                actor_id=principal.actor_id if principal else None,
                role=principal.role.value if principal else None,
            )
            raise

    app = FastAPI(
        title="SmartFlow Next",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(authorized)],
    )
    app.state.db = db
    jobs = Jobs(db)
    engine = Engine(db, Simulator(db), settings.data_dir)

    def failure(code, trace_id, stage=None):
        return JSONResponse(
            {"error": error_payload(code, trace_id, stage)},
            status_code=ERRORS[code].http_status,
            headers={"WWW-Authenticate": "Bearer"} if code == "UNAUTHORIZED" else None,
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
            request.state.error_code = "ORIGIN_REJECTED"
            response = failure("ORIGIN_REJECTED", request.state.trace_id)
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                request.state.error_code = "INTERNAL_ERROR"
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
            job_id=getattr(request.state, "job_id", None),
            command_trace_id=getattr(request.state, "command_trace_id", None),
            code=getattr(request.state, "error_code", None),
            actor_id=getattr(getattr(request.state, "principal", None), "actor_id", None),
            role=getattr(getattr(request.state, "principal", None), "role", None),
        )
        return response

    @app.exception_handler(AppError)
    async def domain_error(request, exc):
        request.state.error_code = exc.code
        return failure(exc.code, request.state.trace_id, getattr(request.state, "job_stage", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic errors may contain user input. Only field location and type are safe.
        request.state.error_code = "INPUT_INVALID"
        # Extra-field keys are user input too. Do not echo arbitrary keys in locations.
        allowed_fields = {
            "body",
            "query",
            "path",
            "header",
            "title",
            "scenario",
            "job_id",
            "action",
            "table",
            "limit",
            "offset",
            "after",
            "idempotency-key",
        }
        fields = [
            {
                "field": ".".join(str(p) if p in allowed_fields else "unknown" for p in e["loc"]),
                "type": e["type"],
            }
            for e in exc.errors()
        ]
        return JSONResponse(
            {"error": error_payload("INPUT_INVALID", request.state.trace_id), "fields": fields},
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        code = {404: "ROUTE_NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "INTERNAL_ERROR")
        request.state.error_code = code
        response = failure(code, request.state.trace_id)
        if exc.status_code == 405 and exc.headers and "Allow" in exc.headers:
            response.headers["Allow"] = exc.headers["Allow"]
        return response

    from fastapi import APIRouter

    router = APIRouter(
        prefix="/api", responses=error_responses(401, 403, 405, 422, 500)
    )

    @router.get("/session", response_model=SessionResponse, openapi_extra=policy(Permission.SESSION_READ))
    def session_info(request: Request):
        principal = request.state.principal
        return {
            "actor_id": principal.actor_id,
            "role": principal.role,
            "auth_mode": principal.auth_mode,
            "permissions": sorted(principal.permissions),
        }

    @router.get("/health", response_model=HealthResponse, openapi_extra=policy(Permission.SESSION_READ))
    def health():
        return {
            **overview(db),
            "mode": settings.mode,
            "worker_alive": getattr(app.state, "worker_alive", lambda: False)(),
        }

    @router.get("/openapi.json", response_model=OpenAPIDocument, openapi_extra=policy(Permission.SCHEMA_READ))
    def openapi():
        return app.openapi()

    @router.get("/errors", response_model=dict[str, ErrorInfo], openapi_extra=policy(Permission.SCHEMA_READ))
    def errors():
        return {code: error_payload(code, "") for code in ERRORS}

    @router.post(
        "/jobs",
        status_code=201,
        response_model=JobResponse,
        responses=error_responses(409),
        openapi_extra=policy(Permission.JOBS_CREATE),
    )
    def create(
        data: CreateJob,
        request: Request,
        idempotency_key: Annotated[str, Header(min_length=8, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")],
    ):
        job = jobs.create(data, idempotency_key, request.state.trace_id)
        request.state.job_id = job["id"]
        emit(
            logger,
            "job.create",
            job_id=job["id"],
            trace_id=job["trace_id"],
            command_trace_id=request.state.trace_id,
        )
        return job

    @router.get("/jobs", response_model=list[JobResponse], openapi_extra=policy(Permission.JOBS_READ))
    def list_jobs(limit: Annotated[int, Query(ge=1, le=200)] = 100, offset: Annotated[int, Query(ge=0)] = 0):
        return jobs.list(limit, offset)

    @router.get(
        "/jobs/{job_id}",
        response_model=JobResponse,
        responses=error_responses(404),
        openapi_extra=policy(Permission.JOBS_READ),
    )
    def get_job(job_id: str):
        return jobs.get(job_id)

    @router.get(
        "/jobs/{job_id}/events",
        openapi_extra=policy(Permission.JOBS_READ),
        response_model=list[EventResponse],
        response_model_exclude_unset=True,
        responses=error_responses(404),
    )
    def events(
        job_id: str, after: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=500)] = 200
    ):
        return jobs.events(job_id, after, limit)

    @router.post(
        "/jobs/{job_id}/commands/{action}",
        response_model=JobResponse,
        responses=error_responses(404, 409),
        openapi_extra=policy(Permission.JOBS_COMMAND),
    )
    def command(job_id: str, action: Literal["resume", "cancel", "reconcile"], request: Request):
        job = jobs.get(job_id)
        request.state.job_id = job["id"]
        request.state.job_stage = job["stage"]
        request.state.command_trace_id = request.state.trace_id
        emit(
            logger,
            "job.command",
            job_id=job["id"],
            trace_id=job["trace_id"],
            command_trace_id=request.state.trace_id,
            stage=job["stage"],
        )
        if action == "reconcile":
            engine.reconcile(job_id, command_trace_id=request.state.trace_id)
            return jobs.get(job_id)
        return jobs.command(job_id, action, command_trace_id=request.state.trace_id)

    @router.get(
        "/jobs/{job_id}/diagnostics",
        openapi_extra=policy(Permission.DIAGNOSTICS_READ),
        response_model=DiagnosticResponse,
        response_model_exclude_unset=True,
        responses=error_responses(404),
    )
    def diagnostic(job_id: str):
        return job_diagnostic(db, job_id)

    @router.get(
        "/jobs/{job_id}/support-bundle",
        openapi_extra=policy(Permission.SUPPORT_EXPORT),
        response_class=Response,
        responses={
            **error_responses(404),
            200: {
                "description": "Allowlisted diagnostic ZIP",
                "content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}},
            },
        },
    )
    def bundle(job_id: str):
        return Response(
            support_bundle(db, job_id),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="smartflow-support.zip"'},
        )

    @router.get(
        "/diagnostics/database",
        response_model=DatabaseResponse,
        openapi_extra=policy(Permission.DIAGNOSTICS_READ),
    )
    def database():
        return database_overview(db)

    @router.get(
        "/diagnostics/logs",
        response_model=list[LogResponse],
        response_model_exclude_unset=True,
        openapi_extra=policy(Permission.DIAGNOSTICS_READ),
    )
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

    @router.get(
        "/diagnostics/database/{table}",
        response_model=list[JobRow | ReceiptRow | EventRow],
        openapi_extra=policy(Permission.DIAGNOSTICS_READ),
    )
    def rows(
        table: Literal["jobs", "receipts", "events"],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        return table_rows(db, table, limit, offset)

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
