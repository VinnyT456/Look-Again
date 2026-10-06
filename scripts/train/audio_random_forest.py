"""Backward-compatible entry point for audio random forest training."""

from scripts.train.audio_classical_ml import main

if __name__ == "__main__":
    import sys

    if "--model" not in sys.argv:
        sys.argv[1:1] = ["--model", "random_forest"]
    main()
