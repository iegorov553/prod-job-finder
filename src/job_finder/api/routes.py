"""API routes for run management."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Header, HTTPException, Request, status

from job_finder.api.auth import AuthorizationError, require_bearer_token
from job_finder.resources import api_messages
from job_finder.run_service import RunInProgressError, RunService

router = APIRouter()


def _get_run_service(request: Request) -> RunService:
    service = cast(RunService | None, getattr(request.app.state, "run_service", None))
    if service is None:
        raise RuntimeError("Run service not configured")
    return service


def _get_token(request: Request) -> str:
    token = getattr(request.app.state, "api_token", "")
    if not token:
        raise RuntimeError("API token not configured")
    return token


@router.post("/api/run", status_code=status.HTTP_202_ACCEPTED)
async def start_run(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    try:
        require_bearer_token(authorization, _get_token(request))
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    service = _get_run_service(request)
    try:
        run = await service.start_background_run()
    except RunInProgressError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=api_messages.RUN_IN_PROGRESS,
        ) from None

    return {"run_id": run.id, "status": run.status}
