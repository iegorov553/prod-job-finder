"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from job_finder.api.routes import router
from job_finder.run_service import RunService


def create_app(run_service: RunService, api_token: str) -> FastAPI:
    app = FastAPI(title="Job Finder API")
    app.state.run_service = run_service
    app.state.api_token = api_token
    app.include_router(router)
    return app
