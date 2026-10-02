import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from smartflow.db import Database
from smartflow.observability import create_logger


def old_database(tmp_path):
    db = Database(tmp_path / "smartflow.db", create_logger(tmp_path))
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "backend/smartflow/migrations"))
    with db.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0001")
        connection.exec_driver_sql("CREATE TABLE private_fixture (value TEXT NOT NULL)")
        connection.exec_driver_sql("INSERT INTO private_fixture VALUES ('PRIVATE_WAL_DATA')")
    return db


def test_wal_backup_preserves_existing_data_and_repeat_migration_is_noop(tmp_path):
    db = old_database(tmp_path)
    try:
        db.migrate()
        backups = list((tmp_path / "backups").glob("*.sqlite3"))
        assert len(backups) == 1
        with sqlite3.connect(backups[0]) as saved:
            assert saved.execute("SELECT value FROM private_fixture").fetchone()[0] == "PRIVATE_WAL_DATA"
            assert saved.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert saved.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0001"
        with db.engine.connect() as current:
            assert current.exec_driver_sql("SELECT value FROM private_fixture").scalar() == "PRIVATE_WAL_DATA"
            assert current.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() == "0003"
        db.migrate()
        assert len(list((tmp_path / "backups").glob("*.sqlite3"))) == 1
    finally:
        db.close()


def test_migration_failure_rolls_back_ddl_and_data_without_replacing_live_db(tmp_path, monkeypatch):
    db = old_database(tmp_path)

    def broken(config, target):
        connection = config.attributes["connection"]
        connection.exec_driver_sql("CREATE TABLE incomplete_upgrade (id INTEGER)")
        connection.exec_driver_sql("UPDATE private_fixture SET value='broken'")
        raise RuntimeError("PRIVATE_FAILURE")

    monkeypatch.setattr("smartflow.migration_safety.command.upgrade", broken)
    try:
        with pytest.raises(RuntimeError):
            db.migrate()
        with db.engine.connect() as connection:
            assert (
                connection.exec_driver_sql("SELECT value FROM private_fixture").scalar() == "PRIVATE_WAL_DATA"
            )
            assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() == "0001"
            assert (
                connection.exec_driver_sql(
                    "SELECT count(*) FROM sqlite_master WHERE name='incomplete_upgrade'"
                ).scalar()
                == 0
            )
        text = (tmp_path / "logs/runtime.jsonl").read_text()
        assert "database.migration_rolled_back" in text and "PRIVATE_FAILURE" not in text
    finally:
        db.close()


def test_backup_failure_prevents_schema_change(tmp_path, monkeypatch):
    db = old_database(tmp_path)
    monkeypatch.setattr(
        "smartflow.migration_safety.sqlite3.connect", lambda *a, **kw: (_ for _ in ()).throw(OSError())
    )
    try:
        with pytest.raises(OSError):
            db.migrate()
        with db.engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() == "0001"
    finally:
        db.close()
