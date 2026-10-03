from uuid import UUID

from fastapi import APIRouter, Request

from smartflow.auth import Permission, policy
from smartflow.browser_bridge import BridgeInfo, PairCode, PairExchange, PairRequest, PairResponse
from smartflow.contracts import error_responses


def bridge_router(bridge):
    router = APIRouter(prefix="/api/browser", responses=error_responses(401, 403, 404, 409, 422, 500))

    @router.get("", response_model=BridgeInfo, openapi_extra=policy(Permission.BROWSER_MANAGE))
    def info(request: Request):
        return bridge.info(request.state.trace_id)

    @router.post("/pairings", response_model=PairCode, openapi_extra=policy(Permission.BROWSER_MANAGE))
    def create(data: PairRequest, request: Request):
        return bridge.create(data, request.state.trace_id)

    @router.post("/pair", response_model=PairResponse, openapi_extra=policy(Permission.BROWSER_PAIR))
    def exchange(data: PairExchange, request: Request):
        return bridge.exchange(request.state.principal, data, request.state.trace_id)

    @router.get("/agent", response_model=PairResponse, openapi_extra=policy(Permission.BROWSER_STATUS))
    def status(request: Request):
        return bridge.status(request.state.principal)

    @router.post(
        "/pairings/{pair_id}/revoke",
        response_model=PairResponse,
        openapi_extra=policy(Permission.BROWSER_MANAGE),
    )
    def revoke(pair_id: UUID, request: Request):
        return bridge.revoke(str(pair_id), request.state.trace_id)

    return router
