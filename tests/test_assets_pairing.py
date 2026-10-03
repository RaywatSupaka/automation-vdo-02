import asyncio
import json
import secrets
from uuid import uuid4

import pytest
from smartflow.asset_models import DraftAsset
from smartflow.assets import Assets, asset_path
from smartflow.auth import AuthMode
from smartflow.browser_bridge import COMPAT, Bridge, PairExchange, PairRequest
from smartflow.draft_contracts import DraftInput
from smartflow.drafts import Drafts
from smartflow.errors import AppError
from sqlalchemy import select

PNG = b"\x89PNG\r\n\x1a\n" + bytes(40)


def draft(client):
    return client.post("/api/story-drafts", json={}, headers={"Idempotency-Key": str(uuid4())}).json()


def upload(client, identifier, data=PNG, key="asset-command", **overrides):
    headers = {
        "Idempotency-Key": key,
        "X-File-Name": "image.png",
        "X-File-Size": str(len(data)),
        "Content-Type": "application/octet-stream",
        **overrides,
    }
    return client.post(
        f"/api/story-drafts/{identifier}/assets?field=mainImage", content=data, headers=headers
    )


def test_asset_roundtrip_duplicate_missing_corruption_and_cross_draft(client):
    one, two = draft(client), draft(client)
    saved = upload(client, one["id"])
    assert saved.status_code == 200, saved.text
    asset = saved.json()
    assert upload(client, one["id"]).json() == asset
    path = f"/api/story-drafts/{one['id']}"
    config = one["config"] | {"mainImage": [asset["id"]]}
    update = client.patch(
        path, json={"expected_revision": 1, "config": config}, headers={"Idempotency-Key": "save-image"}
    )
    assert update.status_code == 200, update.text
    assert client.get(f"{path}/assets/{asset['id']}").content == PNG
    assert client.get(f"/api/story-drafts/{two['id']}/assets/{asset['id']}").status_code == 422
    conflict = upload(client, one["id"], data=PNG[:-1] + b"x")
    assert conflict.status_code == 409
    actual = asset_path(client.app.state.db, asset["id"])
    actual.write_bytes(PNG[:-1] + b"x")
    assert client.get(f"{path}/assets/{asset['id']}").status_code == 422
    actual.unlink()
    assert client.get(f"{path}/assets").json()[0]["missing"]
    assert client.get(path).json()["config"]["mainImage"] == [asset["id"]]
    logs = (client.app.state.db.path.parent / "logs/runtime.jsonl").read_text(encoding="utf-8")
    assert "image.png" not in logs


@pytest.mark.parametrize(
    "data,headers",
    [
        (b"fake png", {}),
        (PNG, {"X-File-Name": "..%2Fprivate.png"}),
        (PNG, {"X-File-Size": "5000000001"}),
        (PNG, {"X-File-Size": "1"}),
    ],
)
def test_invalid_asset_does_not_publish_bytes(client, data, headers):
    row = draft(client)
    assert upload(client, row["id"], data, **headers).status_code == 422
    directory = client.app.state.db.path.parent / "draft-assets"
    assert not list(directory.glob("*.bin")) and not list(directory.glob("*.part"))


def test_interrupted_import_retries_same_identity(system):
    db, *_ = system
    row = Drafts(db).save(DraftInput(), "draft", "trace")

    async def broken():
        yield PNG[:8]
        raise ConnectionError("fixture interruption")

    assets = Assets(db)
    with pytest.raises(AppError, match="DRAFT_SAVE_FAILED"):
        asyncio.run(
            assets.import_file(row["id"], "mainImage", "image.png", len(PNG), "same-key", broken(), "trace")
        )
    assert not list((db.path.parent / "draft-assets").glob("*.part"))

    async def complete():
        yield PNG

    result = asyncio.run(
        assets.import_file(row["id"], "mainImage", "image.png", len(PNG), "same-key", complete(), "trace")
    )
    assert not result["missing"]
    with db.transaction() as session:
        assert len(list(session.scalars(select(DraftAsset)))) == 1


def test_pairing_nonce_idempotency_expiry_revoke_and_agent_scope(client):
    created = client.post("/api/browser/pairings", json={"extension_id": COMPAT["extension_id"]})
    assert created.status_code == 200, created.text
    code = created.json()["code"]
    token = secrets.token_urlsafe(32)
    body = {
        "extension_id": COMPAT["extension_id"],
        "extension_version": "0.2.0",
        "helper_version": "0.2.0",
        "agent_token": token,
    }
    headers = {"Authorization": f"Bearer {code}"}
    assert client.post("/api/browser/pair", json=body, headers=headers).status_code == 200
    assert client.post("/api/browser/pair", json=body, headers=headers).status_code == 200
    assert (
        client.post(
            "/api/browser/pair", json=body | {"agent_token": secrets.token_urlsafe(32)}, headers=headers
        ).status_code
        == 409
    )
    agent = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/browser/agent", headers=agent).json()["connected"]
    for path in ["/api/story-drafts", "/api/jobs", "/api/diagnostics/logs", "/api/browser"]:
        assert client.get(path, headers=agent).status_code == 403
    client.post(f"/api/browser/pairings/{created.json()['id']}/revoke")
    client.post(f"/api/browser/pairings/{created.json()['id']}/revoke")
    from smartflow.browser_bridge import BrowserEvent

    with client.app.state.db.transaction() as session:
        names = list(session.scalars(select(BrowserEvent.name).order_by(BrowserEvent.id)))
    assert names == ["browser.pairing_requested", "browser.paired", "browser.revoked"]
    assert client.get("/api/browser/agent", headers=agent).status_code == 401
    logs = (client.app.state.db.path.parent / "logs/runtime.jsonl").read_text(encoding="utf-8")
    assert token not in logs and code not in logs
    assert [json.loads(line)["event"] for line in logs.splitlines()].count("browser.revoked") == 1


def test_expired_nonce_and_wrong_extension_fail_without_mutation(system):
    db, _, _, clock, _ = system
    bridge = Bridge(db, AuthMode.LOCAL_SESSION, clock)
    row = bridge.create(PairRequest(extension_id=COMPAT["extension_id"]), "trace")
    identity = bridge.authenticate(row["code"])
    body = PairExchange(
        extension_id="a" * 32,
        extension_version="0.2.0",
        helper_version="0.2.0",
        agent_token=secrets.token_urlsafe(32),
    )
    with pytest.raises(AppError, match="EXTENSION_ID_MISMATCH"):
        bridge.exchange(identity, body, "trace")
    clock.advance(121)
    with pytest.raises(AppError, match="UNAUTHORIZED"):
        bridge.authenticate(row["code"])
    # Expiry now persists a transition and audit event, rather than leaving a stale pending row.
    assert bridge.info()["pairings"][0]["state"] == "expired"
    assert bridge.info()["pairings"][0]["state"] == "expired"
    from smartflow.browser_bridge import BrowserEvent, Pairing

    with db.transaction() as session:
        assert session.get(Pairing, row["id"]).state == "expired"
        assert list(session.scalars(select(BrowserEvent.name).order_by(BrowserEvent.id))) == [
            "browser.pairing_requested",
            "browser.expired",
        ]


def test_native_dpapi_and_lost_pair_ack_reuses_protected_pending_token(tmp_path, monkeypatch):
    import httpx
    from smartflow import protected_store
    from smartflow.native_client import NativeClient
    from smartflow.native_host import Hello

    client = NativeClient(
        {
            "port": 8766,
            "extension_id": COMPAT["extension_id"],
            "credential_path": str(tmp_path / "credential.dpapi"),
        }
    )
    payloads = []

    def request(method, path, token, data=None):
        payloads.append(data)
        if len(payloads) == 1:
            raise httpx.ReadTimeout("ACK lost")
        return httpx.Response(200, json={})

    monkeypatch.setattr(client, "request", request)
    message = Hello(
        protocol_version=1,
        message_id=uuid4(),
        kind="pair",
        extension_version="0.2.0",
        code=secrets.token_urlsafe(32),
    )
    assert client.execute(message) == "unavailable"
    assert client.execute(message) == "paired"
    assert payloads[0]["agent_token"] == payloads[1]["agent_token"]
    assert payloads[0]["agent_token"].encode() not in client.path.read_bytes()
    assert protected_store.load(client.path)["active"]["token"] == payloads[0]["agent_token"]
