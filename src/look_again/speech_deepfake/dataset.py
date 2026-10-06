"""PyTorch dataset for raw-waveform speech deepfake training."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch.utils.data import Dataset

from .metadata import SpeechRecord
from .waveform import PreprocessFailure, WaveformExample, load_waveform_example


@dataclass(frozen=True)
class EmbeddingRecord:
    file_path: str
    label: int
    embedding: np.ndarray


class SpeechWaveformDataset(Dataset):
    def __init__(
        self,
        records: list[SpeechRecord],
        *,
        sample_rate: int = 16_000,
        max_audio_seconds: float = 5.0,
    ) -> None:
        self.records = records
        self.sample_rate = sample_rate
        self.max_audio_seconds = max_audio_seconds

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, object]:
        record = self.records[index]
        loaded = load_waveform_example(
            record.absolute_path,
            sample_rate=self.sample_rate,
            max_audio_seconds=self.max_audio_seconds,
        )
        if isinstance(loaded, PreprocessFailure):
            raise RuntimeError(f"Failed to load {record.file_path}: {loaded.reason}")
        return {
            "waveform": loaded.waveform,
            "label": record.label,
            "file_path": record.file_path,
        }


class CachedEmbeddingDataset(Dataset):
    def __init__(self, records: list[EmbeddingRecord]) -> None:
        self.records = records

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, object]:
        record = self.records[index]
        return {
            "embedding": torch.from_numpy(record.embedding.astype(np.float32, copy=False)),
            "label": record.label,
            "file_path": record.file_path,
        }


def collate_waveforms(batch: list[dict[str, object]], processor) -> dict[str, torch.Tensor]:
    waveforms = [item["waveform"] for item in batch]
    labels = torch.tensor([int(item["label"]) for item in batch], dtype=torch.long)
    encoded = processor(
        waveforms,
        sampling_rate=processor.sampling_rate,
        padding=True,
        return_tensors="pt",
    )
    payload = {
        "input_values": encoded["input_values"],
        "labels": labels,
    }
    if "attention_mask" in encoded:
        payload["attention_mask"] = encoded["attention_mask"]
    payload["file_paths"] = [str(item["file_path"]) for item in batch]
    return payload


def collate_embeddings(batch: list[dict[str, object]]) -> dict[str, torch.Tensor]:
    embeddings = torch.stack([item["embedding"] for item in batch], dim=0)
    labels = torch.tensor([int(item["label"]) for item in batch], dtype=torch.long)
    return {"embeddings": embeddings, "labels": labels}
