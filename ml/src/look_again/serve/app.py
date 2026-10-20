"""WildcatVerify detector API.

Run from ml/:
    uv sync --extra serve
    uv run uvicorn look_again.serve.app:app --host 127.0.0.1 --port 8765

Keep it on a private interface: the Next.js app is the only public entry point.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

from look_again.serve.classifier import Detector
from look_again.serve.routes import classify, health

logger = logging.getLogger("look_again.serve")


def _load() -> Detector:
    detector = Detector()
    # The first pass is several times slower; take it before real traffic.
    detector.warm_up()
    return detector


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.detector = None
    app.state.load_error = None
    try:
        app.state.detector = await run_in_threadpool(_load)
        logger.info("Detector loaded")
    except Exception as error:  # noqa: BLE001 - keep serving /health so callers fall back to demo
        app.state.load_error = str(error)
        logger.exception("Couldn't load the detector")
    yield


app = FastAPI(title="WildcatVerify detector", version="1.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(classify.router)
