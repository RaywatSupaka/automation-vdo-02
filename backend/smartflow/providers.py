from typing import Protocol

from smartflow.errors import AppError
from smartflow.models import SimulatedRequest


class Provider(Protocol):
    def preflight(self, scenario: str, attempt: int) -> None: ...
    def submit(self, request_id: str, scenario: str) -> None: ...
    def inspect(self, request_id: str, scenario: str) -> str | None: ...


class Simulator:
    """Offline only. Never calls a real provider or produces a claimed AI video."""

    def __init__(self, db):
        self.db = db

    def preflight(self, scenario, attempt):
        if scenario == "auth_required":
            raise AppError("PROVIDER_AUTH_REQUIRED")
        if scenario == "transient" and attempt < 2:
            raise AppError("PROVIDER_UNAVAILABLE")

    def submit(self, request_id, scenario):
        with self.db.transaction(write=True) as session:
            prior = session.get(SimulatedRequest, request_id)
            if prior:
                # Deliberately count duplicates so tests can detect unsafe dispatch.
                prior.sends += 1
            else:
                session.add(
                    SimulatedRequest(
                        request_id=request_id,
                        sends=1,
                        result="SMARTFLOW SIMULATION CHECKPOINT — no real media was generated.",
                    )
                )
        if scenario == "unknown_send":
            raise AppError("SEND_ACCEPTANCE_UNKNOWN")

    def inspect(self, request_id, scenario):
        if scenario == "pending":
            return None
        with self.db.transaction() as session:
            request = session.get(SimulatedRequest, request_id)
            return request.result if request else None
