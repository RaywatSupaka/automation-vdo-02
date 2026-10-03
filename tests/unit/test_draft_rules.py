import json

import pytest
from smartflow.draft_contracts import REGISTRY, DraftConfig, DraftInput, DraftUpdate, completeness, issues

pytestmark = pytest.mark.unit


def config(**values):
    return {**DraftConfig().model_dump(), **values}


def codes(found):
    return {(issue["field"], issue["code"]) for issue in found}


ASSET = "b6dd00f6-1d87-436c-adc2-94f62b56f5f6"


def test_empty_draft_reports_only_the_visible_required_topic():
    assert completeness(config()) == [{"field": "topic", "code": "FIELD_REQUIRED"}]
    # A whitespace-only topic is still missing; a blank required select or number is too.
    blanks = config(topic="  \n", imageProvider="", videoMode="", scenes="")
    assert codes(completeness(blanks)) == {
        ("topic", "FIELD_REQUIRED"),
        ("imageProvider", "FIELD_REQUIRED"),
        ("videoMode", "FIELD_REQUIRED"),
        ("scenes", "FIELD_REQUIRED"),
    }


@pytest.mark.parametrize(
    ("toggle", "field", "filled"),
    [
        ({"creationMode": "batch"}, "batchTopics", "one\ntwo"),
        ({"visualStyle": "custom"}, "visualCustom", "soft light"),
        ({"introEnabled": True}, "introFile", [ASSET]),
        ({"greenEnabled": True}, "greenFiles", [ASSET]),
        ({"logoEnabled": True}, "logoFile", [ASSET]),
        ({"musicEnabled": True}, "musicFiles", [ASSET]),
        ({"sfxEnabled": True}, "sfxFiles", [ASSET]),
    ],
)
def test_conditional_required_follows_its_controlling_field(toggle, field, filled):
    base = {"topic": "ready"}
    assert completeness(config(**base)) == []  # Off: a hidden empty field is not required.
    on = config(**base, **toggle)
    if field == "batchTopics":
        on["topic"] = ""  # Batch hides the single topic; only the batch list is required.
    assert (field, "FIELD_REQUIRED") in codes(completeness(on))
    assert (field, "FIELD_REQUIRED") not in codes(completeness({**on, field: filled}))


def test_music_count_cannot_exceed_selected_files_only_while_music_is_on():
    two = [ASSET, ASSET.replace("b6", "c7", 1)]
    on = config(topic="ready", musicEnabled=True, musicFiles=two)
    assert completeness({**on, "musicCount": "2"}) == []
    assert completeness({**on, "musicCount": "3"}) == [{"field": "musicCount", "code": "VALUE_OUT_OF_RANGE"}]
    assert completeness({**on, "musicCount": "3", "musicEnabled": False}) == []
    # A value issues() already rejects is reported once, by issues(), not again as a cross-field limit.
    assert completeness({**on, "musicCount": "abc"}) == []
    assert issues({**on, "musicCount": "abc"}) == [{"field": "musicCount", "code": "VALUE_OUT_OF_RANGE"}]


def test_batch_topic_limit_counts_non_blank_lines():
    batch = config(creationMode="batch")
    ten = "\n".join(f"topic {n}" for n in range(10))
    assert completeness({**batch, "batchTopics": ten + "\n\n  \r\n"}) == []
    over = {**batch, "batchTopics": ten + "\r\nextra"}
    assert completeness(over) == [{"field": "batchTopics", "code": "VALUE_OUT_OF_RANGE"}]
    assert completeness({**over, "creationMode": "single", "topic": "ready"}) == []


def test_cover_scene_must_be_auto_or_an_existing_scene():
    ready = config(topic="ready", scenes="8")
    assert completeness({**ready, "coverScene": "8"}) == []
    assert completeness({**ready, "coverScene": "auto"}) == []
    assert completeness({**ready, "coverScene": "9"}) == [{"field": "coverScene", "code": "OPTION_INVALID"}]
    assert completeness({**ready, "coverScene": "9", "aiCover": False}) == []
    assert completeness({**ready, "scenes": "x", "coverScene": "1"}) == [
        {"field": "coverScene", "code": "OPTION_INVALID"}
    ]


# Same table as the coverScene probes in persistence-contract.test.ts: the UI's `Number(scenes) || 0`, clamped.
SCENE_OPTION_COUNTS = {
    "0": 0, "1": 1, "8": 8, "15": 15, "40": 15, "x": 0, "": 0, " 8 ": 8, "8.9": 8,
    "1e1": 10, "1e999": 15, "Infinity": 15, "-Infinity": 0, "0x8": 8, "1_0": 0, "１０": 0,
}  # fmt: skip


@pytest.mark.parametrize(("scenes", "count"), SCENE_OPTION_COUNTS.items())
def test_cover_scene_options_parse_scenes_like_the_ui(scenes, count):
    # Python float() alone would accept "1_0" and full-width digits and reject "0x8", unlike the UI.
    def cover(value):  # Only the coverScene verdict; a blank scenes is reported on scenes itself.
        return [
            i
            for i in completeness(config(topic="ready", scenes=scenes, coverScene=value))
            if i["field"] != "scenes"
        ]

    assert cover("auto") == []
    if count:
        assert cover(str(count)) == []
    assert cover(str(count + 1)) == [{"field": "coverScene", "code": "OPTION_INVALID"}]


def test_music_count_the_ui_cannot_parse_never_trips_the_file_limit():
    two = [ASSET, ASSET.replace("b6", "c7", 1)]
    on = config(topic="ready", musicEnabled=True, musicFiles=two)
    # issues() flags the malformed number; completeness does not report a duplicate cross-field issue.
    assert completeness({**on, "musicCount": "1_0"}) == []
    assert completeness({**on, "musicCount": "0x3"}) == [
        {"field": "musicCount", "code": "VALUE_OUT_OF_RANGE"}
    ]  # Number("0x3") is 3, which exceeds the two selected files.
    assert completeness({**on, "musicCount": " 3 "}) == [
        {"field": "musicCount", "code": "VALUE_OUT_OF_RANGE"}
    ]


@pytest.mark.parametrize(
    ("value", "valid"),
    [("1_0", False), ("１０", False), ("0x8", True), ("1e1", True), ("Infinity", False)],
)
def test_single_field_number_issues_follow_ui_number_parsing(value, valid):
    expected = [] if valid else [{"field": "scenes", "code": "VALUE_OUT_OF_RANGE"}]
    assert issues(config(scenes=value)) == expected


def test_issues_only_checks_single_fields_not_completeness():
    # Job start checks both sets of issues; required and cross-field rules stay in completeness().
    incomplete = config(topic="", musicEnabled=True, musicCount="5", creationMode="batch")
    assert issues(incomplete) == []
    assert issues(config(scenes="-", coverScene="99")) == [{"field": "scenes", "code": "VALUE_OUT_OF_RANGE"}]


def test_rule_metadata_is_well_formed():
    for field, spec in REGISTRY.items():
        if "when" in spec:
            assert set(spec["when"]) == {"field", "equals"}
            source = REGISTRY[spec["when"]["field"]]
            expected = [True, False] if source["kind"] == "checkbox" else source["options"]
            assert spec["when"]["equals"] in expected, field
        if "maxCountOf" in spec:
            assert REGISTRY[spec["maxCountOf"]]["kind"] == "file"
        if "optionsUpTo" in spec:
            assert "max" in REGISTRY[spec["optionsUpTo"]["field"]]


@pytest.fixture
def drafts(tmp_path):
    from smartflow.db import Database
    from smartflow.drafts import Drafts
    from smartflow.observability import create_logger

    db = Database(tmp_path / "smartflow.db", create_logger(tmp_path))
    db.migrate()
    yield Drafts(db, clock=lambda: 1000.0)
    db.close()


def test_saved_draft_response_reports_completeness_and_stays_saveable(drafts):
    created = drafts.save(DraftInput(), "create-key", "trace-create")
    assert created["revision"] == 1
    assert created["issues"] == [{"field": "topic", "code": "FIELD_REQUIRED"}]
    assert drafts.get(created["id"]) == created
    # Duplicate delivery replays the stored ACK, including its issues, without a new revision.
    assert drafts.save(DraftInput(), "create-key", "trace-create") == created

    values = {**created["config"], "topic": "ready", "musicEnabled": True, "musicCount": "2", "scenes": "-"}
    update = DraftUpdate(expected_revision=1, config=values)
    saved = drafts.save(update, "edit-key", "trace-edit", created["id"])
    assert saved["revision"] == 2
    assert saved["issues"] == [
        {"field": "scenes", "code": "VALUE_OUT_OF_RANGE"},
        {"field": "musicFiles", "code": "FIELD_REQUIRED"},
        {"field": "musicCount", "code": "VALUE_OUT_OF_RANGE"},
    ]
    assert json.loads(json.dumps(saved)) == drafts.get(created["id"])


def test_http_draft_routes_report_completeness_but_still_save(client):
    # Route level: the stored ACK, its replay and GET all carry completeness issues; nothing starts a job.
    key = {"Idempotency-Key": "rules-create"}
    created = client.post("/api/story-drafts", json={"config": {"scenes": "-"}}, headers=key)
    assert created.status_code == 201, created.text
    assert created.json()["issues"] == [
        {"field": "scenes", "code": "VALUE_OUT_OF_RANGE"},
        {"field": "topic", "code": "FIELD_REQUIRED"},
    ]
    assert (
        client.post("/api/story-drafts", json={"config": {"scenes": "-"}}, headers=key).json()
        == created.json()
    )
    url = f"/api/story-drafts/{created.json()['id']}"
    assert client.get(url).json() == created.json()
    assert client.get("/api/jobs").json() == []
    ready = {**created.json()["config"], "topic": "ready", "scenes": "8", "coverScene": "9"}
    edited = client.patch(
        url, json={"expected_revision": 1, "config": ready}, headers={"Idempotency-Key": "rules-edit"}
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["issues"] == [{"field": "coverScene", "code": "OPTION_INVALID"}]
    fixed = client.patch(
        url,
        json={"expected_revision": 2, "config": {**ready, "coverScene": "8"}},
        headers={"Idempotency-Key": "rules-fixed"},
    )
    assert fixed.json()["revision"] == 3 and fixed.json()["issues"] == []
