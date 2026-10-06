"""Optional frozen-encoder embedding cache."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from .dataset import CachedEmbeddingDataset, EmbeddingRecord, SpeechWaveformDataset, collate_waveforms
from .metadata import SpeechRecord
from .model import FrozenSpeechDeepfakeModel


def cache_embeddings_for_records(
    records: list[SpeechRecord],
    model: FrozenSpeechDeepfakeModel,
    *,
    output_path: Path,
    batch_size: int,
    sample_rate: int,
    max_audio_seconds: float,
    device: torch.device,
    num_workers: int = 0,
) -> Path:
    dataset = SpeechWaveformDataset(
        records,
        sample_rate=sample_rate,
        max_audio_seconds=max_audio_seconds,
    )
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        collate_fn=lambda batch: collate_waveforms(batch, model.feature_extractor),
    )
    rows: list[dict[str, float | int | str]] = []
    model.eval()
    with torch.no_grad():
        for batch in tqdm(loader, desc="Caching embeddings", unit="batch"):
            embeddings = model.encode(
                batch["input_values"].to(device),
                batch.get("attention_mask").to(device) if batch.get("attention_mask") is not None else None,
            )
            labels = batch["labels"].cpu().numpy()
            file_paths = batch.get("file_paths")
            for index in range(embeddings.shape[0]):
                row: dict[str, float | int | str] = {
                    "file_path": file_paths[index] if file_paths is not None else f"row_{len(rows)}",
                    "label": int(labels[index]),
                }
                vector = embeddings[index].cpu().numpy()
                for dim, value in enumerate(vector):
                    row[f"embedding_{dim}"] = float(value)
                rows.append(row)
    frame = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_path, index=False)
    return output_path


def load_cached_embedding_records(path: Path) -> list[EmbeddingRecord]:
    frame = pd.read_parquet(path)
    embedding_columns = [column for column in frame.columns if column.startswith("embedding_")]
    embedding_columns.sort(key=lambda name: int(name.split("_", maxsplit=1)[1]))
    records: list[EmbeddingRecord] = []
    for _, row in frame.iterrows():
        vector = row[embedding_columns].to_numpy(dtype=np.float32)
        records.append(
            EmbeddingRecord(
                file_path=str(row["file_path"]),
                label=int(row["label"]),
                embedding=vector,
            )
        )
    return records


class CachedEmbeddingModel(torch.nn.Module):
    """Classifier-only wrapper used after embeddings have been precomputed."""

    def __init__(self, classifier: torch.nn.Module) -> None:
        super().__init__()
        self.classifier = classifier

    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        return self.classifier(embeddings)
