# Sequential-frame SDFVD evaluation

Evaluate a saved image-classifier checkpoint on the Hugging Face
[`Hemgg/SDFVD-video-dataset`](https://huggingface.co/datasets/Hemgg/SDFVD-video-dataset)
by running inference on every decoded frame in sequence. A video is classified
as fake when a configurable number of consecutive frames are classified fake.

```bash
uv run python -m scripts.evaluate.sdfvd --run-name efficientnet_b0
uv run python -m scripts.evaluate.sdfvd --run-name inception_resnet_v1_140k --consecutive-fake-frames 3
```

A lower run length flags clips more readily, while a higher value requires a
longer uninterrupted sequence. Use `--sweep-consecutive-fake-frames` to compare
run lengths after one inference pass, or tune the frame threshold with
`--sweep-real-logit-threshold`.

Metrics, per-frame predictions, and per-video predictions are saved under
`results/neural/`. Use `--batch-size` to set the number of frames per inference
batch; predictions are returned to temporal order before applying the
consecutive-frame rule. Frame ROC-AUC uses model frame logits; video ROC-AUC
ranks clips by their longest fake-prediction run.

SDFVD has one split and 106 clips. It is useful for checking the evaluation
pipeline, but is too small for strong generalization claims.
