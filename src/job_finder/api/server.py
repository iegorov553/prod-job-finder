"""Uvicorn server helpers."""

from __future__ import annotations

import asyncio
from typing import Tuple

import uvicorn
from fastapi import FastAPI


def start_server(app: FastAPI, host: str, port: int) -> Tuple[uvicorn.Server, asyncio.Task[None]]:
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    return server, task
