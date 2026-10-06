"""Train a frozen Wav2Vec2/WavLM backbone with a trainable classification head."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from look_again.paths import MIX_AUDIO_DIR
from look_again.speech_deepfake.config import WAV2VEC2_BASE, WAVLM_BASE_PLUS, SpeechDeepfakeConfig
from look_again.speech_deepfake.trainer import train_speech_deepfake


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-name",
        choices=(WAV2VEC2_BASE, WAVLM_BASE_PLUS),
        default=WAV2VEC2_BASE,
    )
    parser.add_argument("--mix-root", type=Path, default=MIX_AUDIO_DIR)
    parser.add_argument("--max-samples", type=int, default=10_000)
    parser.add_argument("--max-audio-seconds", type=float, default=5.0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument(
        "--cache-embeddings",
        action="store_true",
        help="After loading the frozen encoder, cache pooled embeddings to Parquet.",
    )
    parser.add_argument("--embedding-cache-path", type=Path, default=None)
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Run architecture/gradient checks only (no training loop).",
    )
    parser.add_argument(
        "--full-dataset",
        action="store_true",
        help="Use all Mix clips instead of --max-samples.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SpeechDeepfakeConfig(
        model_name=args.model_name,
        max_samples=None if args.full_dataset else args.max_samples,
        max_audio_seconds=args.max_audio_seconds,
        batch_size=args.batch_size,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        dropout=args.dropout,
        hidden_dim=args.hidden_dim,
        random_seed=args.seed,
        num_workers=args.num_workers,
        early_stopping_patience=args.patience,
        cache_embeddings=args.cache_embeddings,
        embedding_cache_path=str(args.embedding_cache_path) if args.embedding_cache_path else None,
    )
    summary = train_speech_deepfake(
        config,
        mix_root=args.mix_root,
        smoke_only=args.smoke_only,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
