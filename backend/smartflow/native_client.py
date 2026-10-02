import hashlib
import secrets
from pathlib import Path

import httpx
from filelock import FileLock, Timeout

from smartflow import protected_store


class NativeClient:
    def __init__(self, config):
        port = config["port"]
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("PORT_INVALID")
        self.base = f"http://127.0.0.1:{port}"
        self.extension_id = config["extension_id"]
        self.path = Path(config["credential_path"])
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def request(self, method, path, token, data=None):
        # No proxy, redirects or URL supplied by an extension/web page.
        with httpx.Client(timeout=4, trust_env=False, follow_redirects=False) as client:
            return client.request(
                method, self.base + path, headers={"Authorization": f"Bearer {token}"}, json=data
            )

    def execute(self, message):
        from smartflow.native_host import HELPER_VERSION

        try:
            with FileLock(str(self.path) + ".lock", timeout=1):
                stored = protected_store.load(self.path)
                if message.kind == "pair":
                    fingerprint = hashlib.sha256(message.code.encode()).hexdigest()
                    pending = stored.get("pending", {})
                    if pending.get("nonce_hash") != fingerprint:
                        pending = {"nonce_hash": fingerprint, "token": secrets.token_urlsafe(32)}
                        stored["pending"] = pending
                        protected_store.save(self.path, stored)  # Before exchange; ACK loss uses same token.
                    response = self.request(
                        "POST",
                        "/api/browser/pair",
                        message.code,
                        {
                            "extension_id": self.extension_id,
                            "agent_token": pending["token"],
                            "extension_version": message.extension_version,
                            "helper_version": HELPER_VERSION,
                        },
                    )
                    if response.is_success:
                        stored["active"] = {"token": pending["token"]}
                        stored.pop("pending", None)
                        protected_store.save(self.path, stored)
                        return "paired"
                    return "pairing_rejected"
                token = stored.get("active", {}).get("token")
                if not token:
                    return "unpaired"
                response = self.request("GET", "/api/browser/agent", token)
                if response.status_code in {401, 403}:
                    return "revoked"
                return "paired" if response.is_success else "unavailable"
        except (OSError, ValueError, Timeout, httpx.HTTPError):
            return "unavailable"
