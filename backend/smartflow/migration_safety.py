"""WAL-aware backups and atomic SQLite schema upgrades; never reset user data."""

import sqlite3
import time
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from filelock import FileLock

from smartflow.observability import emit


def migrate(db):
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    # All program migrations are serialized. Runtime takes app.lock before this
    # and starts its worker only after migration. No restore over a live database.
    with FileLock(str(db.path) + ".migration.lock", timeout=10), db.engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            if connection.exec_driver_sql("PRAGMA quick_check").scalar() != "ok":
                raise RuntimeError("DATABASE_INTEGRITY_FAILED")
            has_version = connection.exec_driver_sql(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            ).scalar()
            current = (
                connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
                if has_version
                else None
            )
            if current:
                script.get_revision(current)  # Unknown revision fails before any schema write.
            if current == head:
                connection.rollback()
                return
            tables = connection.exec_driver_sql(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name!='alembic_version'"
            ).scalar()
            if tables and not current:
                raise RuntimeError("DATABASE_VERSION_MISSING")
            if current:
                backup_dir = db.path.parent / "backups"
                backup_dir.mkdir(exist_ok=True)
                backup = backup_dir / f"before-{current}-{uuid4().hex}.sqlite3"
                deadline = time.monotonic() + 30

                def check_backup_progress(*_):
                    if time.monotonic() > deadline:
                        raise TimeoutError("DATABASE_BACKUP_TIMEOUT")

                # Separate read connection sees committed WAL while the migration
                # connection holds the writer reservation, blocking concurrent writes.
                with sqlite3.connect(db.path.as_uri() + "?mode=ro", uri=True) as source:
                    with sqlite3.connect(backup) as target:
                        source.backup(target, pages=256, progress=check_backup_progress, sleep=0.01)
                        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise RuntimeError("DATABASE_BACKUP_INVALID")
                emit(db.logger, "database.backup_verified", version=current)
            config.attributes["connection"] = connection
            # Explicit BEGIN makes DDL rollback with data if any migration fails.
            command.upgrade(config, "head")
            if connection.exec_driver_sql("PRAGMA integrity_check").scalar() != "ok":
                raise RuntimeError("DATABASE_INTEGRITY_FAILED")
            if connection.exec_driver_sql("PRAGMA foreign_key_check").first():
                raise RuntimeError("DATABASE_FOREIGN_KEY_FAILED")
            connection.commit()
            emit(db.logger, "database.migrated", version=head)
        except BaseException:
            connection.rollback()
            emit(db.logger, "database.migration_rolled_back", code="DATABASE_UPGRADE_FAILED")
            raise
