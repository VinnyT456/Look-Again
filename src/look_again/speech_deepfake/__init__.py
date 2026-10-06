"""Frozen-backbone speech deepfake detection."""

from look_again.speech_deepfake.config import (
    MODEL_SHORT_NAMES,
    WAV2VEC2_BASE,
    WAVLM_BASE_PLUS,
    SpeechDeepfakeConfig,
)
from look_again.speech_deepfake.trainer import run_smoke_checks, train_speech_deepfake

__all__ = [
    "MODEL_SHORT_NAMES",
    "SpeechDeepfakeConfig",
    "WAV2VEC2_BASE",
    "WAVLM_BASE_PLUS",
    "run_smoke_checks",
    "train_speech_deepfake",
]
