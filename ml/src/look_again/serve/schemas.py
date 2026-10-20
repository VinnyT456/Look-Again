"""Response shapes, mirroring `ClassificationResult` in apps/web/src/lib/models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "loading", "error"]
    model_loaded: bool


class HeatmapOut(BaseModel):
    """24×24 per-patch logit contributions, row-major. Positive pushes toward "AI"."""

    grid_size: int = 24
    values: list[float] = Field(min_length=576, max_length=576)


class ClassifyResponse(BaseModel):
    verdict: Literal["real", "ai"]
    """Probability of the winning side, 0–1."""
    confidence: float
    fake_prob: float
    """The detector gives a soft heatmap, never a box, so this is always null."""
    hotspot: None = None
    heatmap: HeatmapOut | None
    is_demo: Literal[False] = False
