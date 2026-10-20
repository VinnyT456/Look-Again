"""Canonical project paths shared by package code and command-line scripts."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"
RESULTS_DIR = PROJECT_ROOT / "results"
CACHE_DIR = PROJECT_ROOT / "cache"
MPLCONFIG_DIR = CACHE_DIR / "matplotlib"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
KAGGLE_140K_DIR = DATA_DIR / "140k-real-and-fake-faces"
REAL_VS_FAKE_140K_DIR = DATA_DIR / "real-vs-fake"
MIX_AUDIO_DIR = PROJECT_ROOT / "Mix"
PROCESSED_DIR = DATA_DIR / "processed"
DEFAULT_AUDIO_FEATURES_PARQUET = PROCESSED_DIR / "audio_features.parquet"
DEFAULT_AUDIO_FEATURES_CSV = PROCESSED_DIR / "audio_features.csv"
DEFAULT_AUDIO_FEATURES_SKIPPED = PROCESSED_DIR / "audio_features_skipped.csv"
DEFAULT_AUDIO_FEATURES_RUN_SUMMARY = PROCESSED_DIR / "audio_features_run_summary.json"
SPEECH_DEEPFAKE_CHECKPOINT_DIR = CHECKPOINT_DIR / "speech_deepfake"
SPEECH_DEEPFAKE_RESULTS_DIR = RESULTS_DIR / "speech_deepfake"
SPEECH_EMBEDDING_CACHE_DIR = CACHE_DIR / "speech_embeddings"
