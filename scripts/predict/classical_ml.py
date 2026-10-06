"""Classify an image with a previously trained classical experiment bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from look_again.classical_ml.inference import predict_image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True, help="Saved .joblib model bundle")
    parser.add_argument("--image", type=Path, required=True, help="Image file to classify")
    args = parser.parse_args()
    with Image.open(args.image) as source:
        result = predict_image(args.model, source)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
