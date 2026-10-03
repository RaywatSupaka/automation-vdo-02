import asyncio
import time

import pytest
from smartflow.assets import Assets
from smartflow.draft_contracts import DraftInput
from smartflow.draft_models import DraftEvent
from smartflow.drafts import Drafts
from sqlalchemy import select

PNG = b"\x89PNG\r\n\x1a\n" + bytes(40)


class Clock:
    def __init__(self, value=5000.0):
        self.value = value

    def __call__(self):
        return self.value


@pytest.fixture
def db(tmp_path):
    from smartflow.db import Database
    from smartflow.observability import create_logger

    database = Database(tmp_path / "smartflow.db", create_logger(tmp_path))
    database.migrate()
    yield database
    database.close()


def asset_events(db, draft_id):
    with db.transaction() as session:
        rows = session.scalars(
            select(DraftEvent)
            .where(DraftEvent.draft_id == draft_id, DraftEvent.name.like("draft.asset_%"))
            .order_by(DraftEvent.id)
        )
        return [(row.name, row.at) for row in rows]


def test_import_persists_injected_clock_and_duplicate_keeps_original_times(db):
    clock = Clock()
    draft = Drafts(db, clock).save(DraftInput(), "draft-key", "trace")
    assets = Assets(db, clock)

    async def stream():
        # Time passes while bytes arrive: reserve and save must read the clock separately.
        clock.value = 5007.5
        yield PNG

    def run():
        return asyncio.run(
            assets.import_file(
                draft["id"], "mainImage", "image.png", len(PNG), "asset-key", stream(), "trace"
            )
        )

    assert not run()["missing"]
    expected = [("draft.asset_reserved", 5000.0), ("draft.asset_saved", 5007.5)]
    assert asset_events(db, draft["id"]) == expected

    # Replaying the same command later must not add events or rewrite persisted times.
    clock.value = 9000.0
    assert not run()["missing"]
    assert asset_events(db, draft["id"]) == expected


def test_default_clock_is_wall_time_for_existing_callers(db):
    # Routes and the Story workflow still construct Assets(db) without a clock.
    draft = Drafts(db).save(DraftInput(), "draft-key", "trace")

    async def stream():
        yield PNG

    before = time.time()
    asyncio.run(
        Assets(db).import_file(
            draft["id"], "mainImage", "image.png", len(PNG), "asset-key", stream(), "trace"
        )
    )
    after = time.time()
    stamps = [at for _, at in asset_events(db, draft["id"])]
    assert len(stamps) == 2 and all(before <= at <= after for at in stamps)
