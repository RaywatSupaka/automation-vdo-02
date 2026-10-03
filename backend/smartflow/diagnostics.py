import io
import json
import zipfile

from sqlalchemy import func, inspect, select

from smartflow import __version__
from smartflow.jobs import Jobs
from smartflow.models import Event, Job, Receipt
from smartflow.story_models import OperationReceipt, StoryOperation


def overview(db):
    with db.transaction() as session:
        counts = dict(session.execute(select(Job.status, func.count()).group_by(Job.status)).all())
        return {
            "version": __version__,
            "database": "connected",
            "provider": "simulator",
            "simulation": True,
            "job_counts": counts,
            "events": session.scalar(select(func.count()).select_from(Event)),
            "schema_revision": session.connection()
            .exec_driver_sql("SELECT version_num FROM alembic_version")
            .scalar(),
        }


def database_overview(db):
    inspector = inspect(db.engine)
    return {
        "tables": [
            {
                "name": name,
                "columns": [
                    {"name": c["name"], "type": str(c["type"]), "nullable": c["nullable"]}
                    for c in inspector.get_columns(name)
                ],
            }
            for name in inspector.get_table_names()
        ]
    }


def job_diagnostic(db, job_id):
    jobs = Jobs(db)
    job = jobs.get(job_id, private=False)
    with db.transaction() as session:
        total = session.scalar(select(func.count()).select_from(Event).where(Event.job_id == job_id))
        latest = list(
            session.scalars(
                select(Event.id).where(Event.job_id == job_id).order_by(Event.id.desc()).limit(200)
            )
        )
        after = min(latest) - 1 if latest else 0
    return {
        "job": job,
        "events": jobs.events(job_id, after),
        "events_total": total,
        "events_truncated": total > 200,
        "conclusion": job["error"] or {"code": "NO_ACTIVE_ERROR", "stage": job["stage"]},
    }


def support_bundle(db, job_id):
    payload = {
        "format_version": 1,
        "app": overview(db),
        "diagnostic": job_diagnostic(db, job_id),
        "privacy": "Allowlisted status only; no title, prompt, provider result, token or raw database.",
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.json", json.dumps(payload, ensure_ascii=False, indent=2))
    return output.getvalue()


def table_rows(db, table, limit, offset=0):
    # Fixed projections only. Never accept arbitrary SQL from the HTTP boundary.
    columns = {
        "jobs": (Job.id, Job.status, Job.stage, Job.error_code, Job.trace_id, Job.updated_at),
        "receipts": (Receipt.job_id, Receipt.request_id, Receipt.state, Receipt.updated_at),
        "events": (Event.id, Event.job_id, Event.trace_id, Event.at, Event.name, Event.stage, Event.code),
        "story_operations": (
            StoryOperation.id,
            StoryOperation.job_id,
            StoryOperation.revision_id,
            StoryOperation.pair_id,
            StoryOperation.lease_epoch,
            StoryOperation.lease_until,
            StoryOperation.deadline,
        ),
        "operation_receipts": (
            OperationReceipt.operation_id,
            OperationReceipt.request_id,
            OperationReceipt.state,
            OperationReceipt.sha256,
            OperationReceipt.updated_at,
        ),
    }[table]
    order = {
        "jobs": (Job.created_at.desc(), Job.id.desc()),
        "receipts": (Receipt.updated_at.desc(), Receipt.job_id.desc()),
        "events": (Event.id.desc(),),
        "story_operations": (StoryOperation.deadline.desc(), StoryOperation.id.desc()),
        "operation_receipts": (OperationReceipt.updated_at.desc(), OperationReceipt.operation_id.desc()),
    }[table]
    with db.transaction() as session:
        return [
            dict(row._mapping)
            for row in session.execute(select(*columns).order_by(*order).offset(offset).limit(limit))
        ]
