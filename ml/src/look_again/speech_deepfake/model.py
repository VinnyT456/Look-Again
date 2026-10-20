"""Frozen Hugging Face speech encoder + trainable head."""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
from transformers import AutoFeatureExtractor, AutoModel

from .classifier_head import SpeechClassifierHead
from .pooling import MaskedMeanPooling, hidden_state_attention_mask


@dataclass(frozen=True)
class ParameterSummary:
    total: int
    frozen: int
    trainable: int

    @property
    def trainable_pct(self) -> float:
        return 100.0 * self.trainable / max(self.total, 1)


def summarize_parameters(model: nn.Module) -> ParameterSummary:
    total = 0
    trainable = 0
    for parameter in model.parameters():
        count = parameter.numel()
        total += count
        if parameter.requires_grad:
            trainable += count
    return ParameterSummary(total=total, frozen=total - trainable, trainable=trainable)


def freeze_module(module: nn.Module) -> None:
    module.eval()
    for parameter in module.parameters():
        parameter.requires_grad = False


class FrozenSpeechDeepfakeModel(nn.Module):
    """Shared Wav2Vec2/WavLM pipeline with a frozen encoder and trainable head."""

    def __init__(
        self,
        model_name: str,
        *,
        hidden_dim: int = 256,
        dropout: float = 0.3,
        activation: str = "gelu",
        num_classes: int = 2,
    ) -> None:
        super().__init__()
        self.model_name = model_name
        self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
        self.encoder = AutoModel.from_pretrained(model_name)
        freeze_module(self.encoder)
        encoder_hidden = int(self.encoder.config.hidden_size)
        self.pooling = MaskedMeanPooling()
        self.classifier = SpeechClassifierHead(
            encoder_hidden,
            hidden_dim=hidden_dim,
            num_classes=num_classes,
            dropout=dropout,
            activation=activation,
        )

    @property
    def trainable_parameters(self) -> list[nn.Parameter]:
        return [parameter for parameter in self.classifier.parameters() if parameter.requires_grad]

    def encode(
        self,
        input_values: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        with torch.no_grad():
            outputs = self.encoder(input_values=input_values, attention_mask=attention_mask)
        hidden = outputs.last_hidden_state
        pooling_mask = hidden_state_attention_mask(self.encoder, hidden, attention_mask)
        return self.pooling(hidden, pooling_mask)

    def forward(
        self,
        input_values: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        embeddings = self.encode(input_values, attention_mask)
        return self.classifier(embeddings)

    def verify_trainable_subset(self) -> None:
        for name, parameter in self.named_parameters():
            should_train = name.startswith("classifier.")
            if parameter.requires_grad != should_train:
                raise RuntimeError(
                    f"Unexpected requires_grad={parameter.requires_grad} for parameter {name}"
                )
