from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from smartflow.observability import emit


class Database:
    def __init__(self, path: Path, logger):
        self.path = path
        self.logger = logger
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False})

        @event.listens_for(self.engine, "connect")
        def configure(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("PRAGMA synchronous=FULL")

    def migrate(self):
        from smartflow.migration_safety import migrate

        migrate(self)

    @contextmanager
    def transaction(self, write=False):
        with Session(self.engine, expire_on_commit=False) as session:
            if write:
                # Serialize claims and command deduplication across processes.
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield session
                session.commit()
                for fields in session.info.get("events", []):
                    emit(self.logger, "job.event", **fields)
            except BaseException:
                session.rollback()
                raise

    def close(self):
        self.engine.dispose()
