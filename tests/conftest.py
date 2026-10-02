import pytest

TOKEN = "test-session-token-never-production"


class Clock:
    value = 1000.0

    def __call__(self):
        return self.value

    def advance(self, seconds=10):
        self.value += seconds


@pytest.fixture
def system(tmp_path):
    from smartflow.db import Database
    from smartflow.engine import Engine
    from smartflow.jobs import CreateJob, Jobs
    from smartflow.observability import create_logger
    from smartflow.providers import Simulator

    clock = Clock()
    db = Database(tmp_path / "smartflow.db", create_logger(tmp_path))
    db.migrate()
    jobs = Jobs(db, clock)
    engine = Engine(db, Simulator(db), tmp_path, clock)

    def create(scenario="success", title="Test job", key="test-command"):
        return jobs.create(CreateJob(title=title, scenario=scenario), key, "test-trace")

    yield db, jobs, engine, clock, create
    db.close()


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient
    from smartflow.api import create_app
    from smartflow.config import Settings

    app = create_app(Settings(tmp_path, TOKEN, "test", 8766))
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as client:
        yield client
