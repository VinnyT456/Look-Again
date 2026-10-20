"""Training loop for frozen-backbone speech deepfake models."""

from __future__ import annotations

import json
import random
import time
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from look_again.paths import MIX_AUDIO_DIR, SPEECH_DEEPFAKE_CHECKPOINT_DIR, SPEECH_DEEPFAKE_RESULTS_DIR

from .checkpointing import save_head_checkpoint, write_training_history
from .config import MODEL_SHORT_NAMES, SpeechDeepfakeConfig
from .dataset import SpeechWaveformDataset, collate_waveforms
from .embedding_cache import cache_embeddings_for_records
from .metadata import build_speech_records
from .metrics import collect_predictions, compute_metrics, resolve_device, write_metrics_bundle
from .model import FrozenSpeechDeepfakeModel, summarize_parameters
from .splits import format_split_summary, split_records


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def run_smoke_checks(model: FrozenSpeechDeepfakeModel, device: torch.device) -> None:
    model.to(device)
    summary = summarize_parameters(model)
    model.verify_trainable_subset()
    print(
        "Parameter summary: "
        f"total={summary.total:,} frozen={summary.frozen:,} "
        f"trainable={summary.trainable:,} ({summary.trainable_pct:.4f}%)"
    )
    processor = model.feature_extractor
    batch_size = 2
    sample_length = int(processor.sampling_rate * 1.5)
    waveforms = [
        np.random.randn(sample_length).astype(np.float32) * 0.01,
        np.random.randn(sample_length).astype(np.float32) * 0.01,
    ]
    encoded = processor(
        waveforms,
        sampling_rate=processor.sampling_rate,
        padding=True,
        return_tensors="pt",
    )
    input_values = encoded["input_values"].to(device)
    attention_mask = encoded.get("attention_mask")
    if attention_mask is not None:
        attention_mask = attention_mask.to(device)
    print(f"Waveform batch shape: {tuple(input_values.shape)}")
    with torch.no_grad():
        outputs = model.encoder(input_values=input_values, attention_mask=attention_mask)
    hidden = outputs.last_hidden_state
    from .pooling import hidden_state_attention_mask

    pooling_mask = hidden_state_attention_mask(model.encoder, hidden, attention_mask)
    pooled = model.pooling(hidden, pooling_mask)
    logits = model.classifier(pooled)
    print(f"Encoder hidden shape: {tuple(hidden.shape)}")
    print(f"Pooled embedding shape: {tuple(pooled.shape)}")
    print(f"Classifier logits shape: {tuple(logits.shape)}")
    labels = torch.tensor([0, 1], device=device)
    loss = nn.CrossEntropyLoss()(logits, labels)
    print(f"Loss: {float(loss.item()):.6f}")
    model.train()
    model.encoder.eval()
    logits = model(input_values, attention_mask)
    loss = nn.CrossEntropyLoss()(logits, labels)
    loss.backward()
    encoder_has_grad = any(
        parameter.grad is not None and float(parameter.grad.abs().max()) > 0.0
        for parameter in model.encoder.parameters()
    )
    head_grad = max(float(parameter.grad.abs().max()) for parameter in model.classifier.parameters())
    if encoder_has_grad:
        raise RuntimeError("Encoder received gradients during smoke test")
    if head_grad == 0.0 or not torch.isfinite(torch.tensor(head_grad)):
        raise RuntimeError("Classifier head did not receive finite gradients")
    print(f"Classifier max grad: {head_grad:.6f}; encoder max grad: 0.000000")


def _run_epoch(
    model: FrozenSpeechDeepfakeModel,
    dataloader: DataLoader,
    *,
    device: torch.device,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    use_amp: bool,
    train: bool,
) -> float:
    if train:
        model.train()
        model.encoder.eval()
    else:
        model.eval()
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp and device.type == "cuda")
    losses: list[float] = []
    for batch in dataloader:
        labels = batch["labels"].to(device)
        attention_mask = batch.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(device)
        input_values = batch["input_values"].to(device)
        if train:
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=use_amp and device.type in {"cuda", "mps"}):
                logits = model(input_values, attention_mask)
                loss = criterion(logits, labels)
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite loss during training")
            if use_amp and device.type == "cuda":
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()
        else:
            with torch.no_grad():
                logits = model(input_values, attention_mask)
                loss = criterion(logits, labels)
        losses.append(float(loss.item()))
    return float(np.mean(losses)) if losses else 0.0


def train_speech_deepfake(
    config: SpeechDeepfakeConfig,
    *,
    mix_root: Path = MIX_AUDIO_DIR,
    results_root: Path = SPEECH_DEEPFAKE_RESULTS_DIR,
    checkpoint_root: Path = SPEECH_DEEPFAKE_CHECKPOINT_DIR,
    smoke_only: bool = False,
) -> dict[str, Any]:
    set_seed(config.random_seed)
    device, amp_supported = resolve_device(config.use_amp)
    use_amp = config.use_amp and amp_supported
    print(f"Using device: {device} (amp={use_amp})")

    records = build_speech_records(
        mix_root,
        max_samples=config.max_samples,
        random_seed=config.random_seed,
    )
    split = split_records(
        records,
        train_ratio=config.train_ratio,
        val_ratio=config.val_ratio,
        test_ratio=config.test_ratio,
        random_seed=config.random_seed,
    )
    split_summary = format_split_summary(split)
    print("Split class counts:", json.dumps(split_summary, indent=2))

    short_name = MODEL_SHORT_NAMES.get(config.model_name, config.model_name.split("/")[-1])
    run_results_dir = results_root / short_name
    run_checkpoint_dir = checkpoint_root / short_name
    run_results_dir.mkdir(parents=True, exist_ok=True)
    (run_results_dir / "split_summary.json").write_text(
        json.dumps(split_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metadata_rows = [
        {
            "file_path": record.file_path,
            "label": record.label_name,
            "speaker_id": record.speaker_id,
            "group_id": record.group_id,
            "source_bucket": record.source_bucket,
            "generation_hint": record.generation_hint,
            "split": split_name,
        }
        for split_name, split_records in (
            ("train", split.train),
            ("validation", split.validation),
            ("test", split.test),
        )
        for record in split_records
    ]
    import csv

    metadata_path = run_results_dir / "split_metadata.csv"
    with metadata_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metadata_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metadata_rows)

    model = FrozenSpeechDeepfakeModel(
        config.model_name,
        hidden_dim=config.hidden_dim,
        dropout=config.dropout,
        activation=config.activation,
    )
    run_smoke_checks(model, device)
    if smoke_only:
        return {"smoke_only": True, "model_name": config.model_name}

    if config.cache_embeddings:
        cache_path = Path(config.embedding_cache_path or run_results_dir / "embeddings.parquet")
        cache_embeddings_for_records(
            records,
            model,
            output_path=cache_path,
            batch_size=config.batch_size,
            sample_rate=config.sample_rate,
            max_audio_seconds=config.max_audio_seconds,
            device=device,
            num_workers=config.num_workers,
        )
        print(f"Cached embeddings to {cache_path}")

    train_loader = DataLoader(
        SpeechWaveformDataset(
            split.train,
            sample_rate=config.sample_rate,
            max_audio_seconds=config.max_audio_seconds,
        ),
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        collate_fn=partial(collate_waveforms, processor=model.feature_extractor),
    )
    val_loader = DataLoader(
        SpeechWaveformDataset(
            split.validation,
            sample_rate=config.sample_rate,
            max_audio_seconds=config.max_audio_seconds,
        ),
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        collate_fn=partial(collate_waveforms, processor=model.feature_extractor),
    )
    test_loader = DataLoader(
        SpeechWaveformDataset(
            split.test,
            sample_rate=config.sample_rate,
            max_audio_seconds=config.max_audio_seconds,
        ),
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        collate_fn=partial(collate_waveforms, processor=model.feature_extractor),
    )

    model.to(device)
    optimizer = torch.optim.AdamW(
        model.trainable_parameters,
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    criterion = nn.CrossEntropyLoss()
    best_val_f1 = -1.0
    best_epoch = -1
    patience_counter = 0
    history_rows: list[dict[str, Any]] = []
    best_checkpoint = run_checkpoint_dir / "best_head.pt"

    for epoch in range(1, config.epochs + 1):
        started = time.perf_counter()
        train_loss = _run_epoch(
            model,
            train_loader,
            device=device,
            optimizer=optimizer,
            criterion=criterion,
            use_amp=use_amp,
            train=True,
        )
        val_loss = _run_epoch(
            model,
            val_loader,
            device=device,
            optimizer=optimizer,
            criterion=criterion,
            use_amp=use_amp,
            train=False,
        )
        y_true, y_pred, y_prob = collect_predictions(model, val_loader, device)
        val_metrics = compute_metrics(y_true, y_pred, y_prob, split_name="validation")
        epoch_seconds = time.perf_counter() - started
        history_rows.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "validation_loss": val_loss,
                "validation_f1": val_metrics["f1"],
                "validation_accuracy": val_metrics["accuracy"],
                "epoch_seconds": epoch_seconds,
            }
        )
        print(
            f"Epoch {epoch}/{config.epochs} "
            f"train_loss={train_loss:.4f} val_loss={val_loss:.4f} val_f1={val_metrics['f1']:.4f}"
        )
        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
            best_epoch = epoch
            patience_counter = 0
            save_head_checkpoint(best_checkpoint, model, config, metrics=val_metrics)
        else:
            patience_counter += 1
            if patience_counter >= config.early_stopping_patience:
                print(f"Early stopping at epoch {epoch} (best epoch {best_epoch})")
                break

    write_training_history(history_rows, run_results_dir / "training_history.csv")
    if not best_checkpoint.is_file():
        save_head_checkpoint(best_checkpoint, model, config)

    checkpoint = torch.load(best_checkpoint, map_location=device, weights_only=False)
    model.classifier.load_state_dict(checkpoint["classifier_state_dict"])
    model.to(device)

    metrics_by_split: dict[str, dict[str, Any]] = {}
    probabilities_by_split: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for split_name, loader in (
        ("train", train_loader),
        ("validation", val_loader),
        ("test", test_loader),
    ):
        y_true, y_pred, y_prob = collect_predictions(model, loader, device)
        metrics_by_split[split_name] = compute_metrics(y_true, y_pred, y_prob, split_name=split_name)
        probabilities_by_split[split_name] = (y_true, y_prob)
    write_metrics_bundle(metrics_by_split, probabilities_by_split, run_results_dir)
    summary = {
        "model_name": config.model_name,
        "best_checkpoint": str(best_checkpoint.resolve()),
        "best_epoch": best_epoch,
        "best_validation_f1": best_val_f1,
        "metrics": metrics_by_split,
        "split_summary": split_summary,
        "training_config": config.to_dict(),
    }
    (run_results_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary
