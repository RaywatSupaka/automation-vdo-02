import pytest
from filelock import FileLock, Timeout
from pydantic import ValidationError
from smartflow.errors import ERRORS
from smartflow.jobs import CreateJob

pytestmark = pytest.mark.unit


def test_every_error_has_recovery_and_safe_message():
    assert all(spec.message and spec.recovery for spec in ERRORS.values())
    assert ERRORS["SEND_ACCEPTANCE_UNKNOWN"].recovery == "inspect_existing_request"


def test_blank_title_and_extra_fields_rejected():
    with pytest.raises(ValidationError):
        CreateJob(title="  ")
    with pytest.raises(ValidationError):
        CreateJob(title="valid", unsafe="value")


def test_worker_lock_rejects_second_owner(tmp_path):
    path = str(tmp_path / "worker.lock")
    with FileLock(path, timeout=0):
        with pytest.raises(Timeout):
            with FileLock(path, timeout=0):
                pass


def test_migration_is_repeatable_and_unknown_version_is_not_reset(system):
    from alembic.util.exc import CommandError

    db, *_ = system
    db.migrate()
    with db.engine.begin() as connection:
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() == "0001"
        connection.exec_driver_sql("UPDATE alembic_version SET version_num='future_version'")
    with pytest.raises(CommandError):
        db.migrate()


def test_windowless_start_failure_is_logged_without_private_message(tmp_path, monkeypatch):
    import sys

    from smartflow.cli import main

    def broken(*args):
        raise RuntimeError("PRIVATE_EXCEPTION_DETAIL")

    monkeypatch.setattr("smartflow.runtime.desktop", broken)
    monkeypatch.setattr(sys, "argv", ["smartflow", "desktop", "--desktop-smoke"])
    monkeypatch.setenv("SMARTFLOW_DATA_DIR", str(tmp_path))
    assert main() == 1
    text = (tmp_path / "logs/runtime.jsonl").read_text(encoding="utf-8")
    assert "desktop.start_failed" in text and "RuntimeError" in text
    assert "PRIVATE_EXCEPTION_DETAIL" not in text
