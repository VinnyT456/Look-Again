"""Run smoke checks for both frozen speech encoders."""

from __future__ import annotations

import argparse

from look_again.speech_deepfake.config import WAV2VEC2_BASE, WAVLM_BASE_PLUS, SpeechDeepfakeConfig
from look_again.speech_deepfake.trainer import train_speech_deepfake


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    for model_name in (WAV2VEC2_BASE, WAVLM_BASE_PLUS):
        print(f"\n=== Smoke test: {model_name} ===")
        config = SpeechDeepfakeConfig(model_name=model_name, max_samples=100)
        train_speech_deepfake(config, smoke_only=True)


if __name__ == "__main__":
    main()
