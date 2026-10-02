from smartflow.config import Settings
from smartflow.offline import diagnose


def test_offline_inspection_does_not_create_database(tmp_path):
    result = diagnose(Settings(tmp_path, ""))
    assert result["database"] == "missing"
    assert not (tmp_path / "smartflow.db").exists()


def test_offline_inspection_reads_counts_without_titles(system):
    db, jobs, engine, clock, create = system
    create(title="PRIVATE_TITLE")
    report = diagnose(Settings(engine.data_dir, ""))
    assert report["job_counts"] == {"queued": 1}
    assert report["schema_revision"] == "0002"
    assert "PRIVATE_TITLE" not in str(report)


def test_corrupt_database_is_reported_without_replacement(tmp_path):
    path = tmp_path / "smartflow.db"
    original = b"not a database: PRIVATE_CONTENT"
    path.write_bytes(original)
    report = diagnose(Settings(tmp_path, ""))
    assert report["database"] == "unreadable"
    assert "PRIVATE_CONTENT" not in str(report)
    assert path.read_bytes() == original
