"""Configuration for frozen-backbone speech deepfake training."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SpeechDeepfakeConfig:
    model_name: str = "facebook/wav2vec2-base-960h"
    sample_rate: int = 16_000
    max_audio_seconds: float = 5.0
    random_seed: int = 42
    max_samples: int | None = 10_000
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1
    batch_size: int = 8
    epochs: int = 10
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    dropout: float = 0.3
    hidden_dim: int = 256
    activation: str = "gelu"
    early_stopping_patience: int = 3
    num_workers: int = 0
    cache_embeddings: bool = False
    embedding_cache_path: str | None = None
    use_amp: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


WAV2VEC2_BASE = "facebook/wav2vec2-base-960h"
WAVLM_BASE_PLUS = "microsoft/wavlm-base-plus"

MODEL_SHORT_NAMES = {
    WAV2VEC2_BASE: "wav2vec2",
    WAVLM_BASE_PLUS: "wavlm",
}

# User-specified label convention for the neural pipeline.
LABEL_REAL = 0
LABEL_FAKE = 1
CLASS_NAMES = ("real", "fake")
