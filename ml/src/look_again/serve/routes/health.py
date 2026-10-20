from __future__ import annotations

from fastapi import APIRouter, Request

from look_again.serve.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    state = request.app.state
    if state.detector is not None:
        return HealthResponse(status="ok", model_loaded=True)
    return HealthResponse(status="error" if state.load_error else "loading", model_loaded=False)
