"""LiteRT-Torch worker (Python 3.12). Invoked by export_probe_tflite when litert_torch is unavailable."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

_WORKER_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _WORKER_DIR.parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_WORKER_DIR))

from probe_export_common import build_universal_probe_module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        import litert_torch
    except ImportError as exc:
        print(
            "litert-torch is required on Python 3.12 for Android export.\n"
            "  uv venv --python 3.12 .venv-litert\n"
            "  uv pip install --python .venv-litert/bin/python litert-torch\n"
            "  uv pip install --python .venv-litert/bin/python -e .",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    probe_module, _processor, _pipeline, _y_train = build_universal_probe_module(torch.device("cpu"))
    example = torch.randn(1, 3, 384, 384, dtype=torch.float32)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    edge = litert_torch.convert(probe_module, (example,))
    edge.export(str(args.output))


if __name__ == "__main__":
    main()
