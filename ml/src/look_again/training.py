import os
from pathlib import Path
from typing import Callable

from look_again.paths import CHECKPOINT_DIR, MPLCONFIG_DIR, RESULTS_DIR
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))

import timm
import matplotlib.pyplot as plt
import seaborn as sns
import torch
import torch.nn as nn
from torch.utils.data import ConcatDataset, DataLoader
from torchvision import transforms

from look_again.dataset import SEED, build_image_splits, grouped_split_with_transform, hold_out_validation_split
from look_again.forensic_preprocessing import (
    FORENSIC_CHANNEL_ORDER,
    FORENSIC_INPUT_CHANNELS,
    ForensicChannelsTransform,
)
from look_again.inception_resnet_v1_checkpoint import INCEPTION_MODEL_NAME, load_inception_resnet_v1_checkpoint
from look_again.robustness import (
    RandomJPEGCompression,
    build_baseline_test_transform,
    run_robustness_evaluation,
)


BATCH_SIZE = 32
EPOCHS = 10
NEURAL_RESULTS_DIR = RESULTS_DIR / "neural"


SUPPORTED_TIMM_MODELS = frozenset(
    {
        "efficientnet_b0",
        "mobilenetv3_large_100",
        "mobilenetv3_small_100",
    }
)


def _make_dense_head(input_features):
    widths = (input_features, 640, 320, 160, 80, 40, 20, 5, 1)
    layers = []
    for index, (input_width, output_width) in enumerate(zip(widths, widths[1:])):
        layers.append(nn.Linear(input_width, output_width))
        if index < len(widths) - 2:
            layers.append(nn.ReLU())
    return nn.Sequential(*layers)


def build_train_transform(model, *, augment: bool = False) -> Callable:
    if getattr(model, "uses_forensic_channels", False):
        return ForensicChannelsTransform(model, augment=augment)

    input_size = tuple(model.default_cfg.get("input_size", (3, 224, 224))[-2:])
    mean = model.default_cfg["mean"]
    std = model.default_cfg["std"]
    steps: list = []
    if augment:
        steps.append(transforms.RandomHorizontalFlip(p=0.5))
        if getattr(model, "face_swap_recipe", False):
            steps.append(RandomJPEGCompression())
        else:
            steps.append(
                transforms.ColorJitter(
                    brightness=0.15,
                    contrast=0.15,
                    saturation=0.1,
                    hue=0.02,
                )
            )
    steps.append(transforms.Resize(input_size))
    steps.extend(
        [
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )
    return transforms.Compose(steps)


def build_dataloaders(
    model,
    *,
    dataset_path: str | Path | None = None,
    train_augmentation: bool = False,
    val_fraction: float = 0.0,
    supplement_celeb_train: bool = False,
    celeb_max_per_class: int = 750,
    supplement_kenjon_train: bool = False,
    kenjon_max_samples: int = 800,
    balance_train_sources: bool = True,
):
    train_transform = build_train_transform(model, augment=train_augmentation)
    eval_transform = build_baseline_test_transform(model)
    dataset_root = (
        Path(dataset_path).expanduser().resolve()
        if dataset_path is not None
        else None
    )

    val_split = None
    if dataset_root is not None:
        from look_again.dataset_140k import is_140k_style_dataset, try_build_140k_grouped_splits

        if is_140k_style_dataset(dataset_root):
            predefined = try_build_140k_grouped_splits(
                dataset_root,
                train_transform=train_transform,
                eval_transform=eval_transform,
            )
            if predefined is None:
                raise ValueError(
                    f"140K dataset at {dataset_root} needs train/ and test/ splits "
                    "or use scripts.train.inception_resnet_v1_140k for flat layouts."
                )
            train_split, val_split, test_split = predefined
            train_core = grouped_split_with_transform(train_split, train_transform)
            if val_split is None and val_fraction > 0:
                train_core, val_split = hold_out_validation_split(
                    train_core,
                    val_fraction=val_fraction,
                )
            elif val_split is not None and val_fraction > 0:
                print(
                    "Using dataset validation split; --val-fraction ignored for 140K layout.",
                    flush=True,
                )
        else:
            train_split, test_split = build_image_splits(
                train_transform=eval_transform,
                test_transform=eval_transform,
                dataset_path=dataset_root,
            )
            val_split = None
            train_core = train_split
            if val_fraction > 0:
                train_core, val_split = hold_out_validation_split(
                    train_split,
                    val_fraction=val_fraction,
                )
            train_core = grouped_split_with_transform(train_core, train_transform)
            if val_split is not None:
                val_split = grouped_split_with_transform(val_split, eval_transform)
    else:
        train_split, test_split = build_image_splits(
            train_transform=eval_transform,
            test_transform=eval_transform,
            dataset_path=dataset_path,
        )
        val_split = None
        train_core = train_split
        if val_fraction > 0:
            train_core, val_split = hold_out_validation_split(
                train_split,
                val_fraction=val_fraction,
            )
        train_core = grouped_split_with_transform(train_core, train_transform)
        if val_split is not None:
            val_split = grouped_split_with_transform(val_split, eval_transform)

    train_dataset: ConcatDataset | torch.utils.data.Subset = train_core.dataset
    source_lengths = [len(train_core.dataset)]
    train_parts: list[torch.utils.data.Subset] = [train_core.dataset]

    if supplement_celeb_train:
        from look_again.celeb_supplement import build_celeb_train_supplement

        supplement, supplement_meta = build_celeb_train_supplement(
            train_transform,
            max_per_class=celeb_max_per_class,
        )
        train_parts.append(supplement)
        source_lengths.append(len(supplement))
        print(
            "Celeb-DF train supplement: "
            f"fake={supplement_meta['fake_count']} real={supplement_meta['real_count']} "
            f"(HF split={supplement_meta['split']})",
            flush=True,
        )

    if supplement_kenjon_train:
        from look_again.kenjon_supplement import build_kenjon_train_supplement

        kenjon_supplement, kenjon_meta = build_kenjon_train_supplement(
            train_transform,
            max_samples=kenjon_max_samples,
        )
        train_parts.append(kenjon_supplement)
        source_lengths.append(len(kenjon_supplement))
        print(
            "Kenjon train supplement: "
            f"samples={kenjon_meta['samples']} (HF split={kenjon_meta['split']}, all fake)",
            flush=True,
        )

    if len(train_parts) > 1:
        train_dataset = ConcatDataset(train_parts)
    else:
        train_dataset = train_parts[0]

    use_balanced_sampler = balance_train_sources and len(source_lengths) > 1
    if use_balanced_sampler:
        train_sampler = build_balanced_source_sampler(source_lengths)
        print(
            "Balanced train sampling across sources: "
            + ", ".join(str(length) for length in source_lengths),
            flush=True,
        )
        train_dataloader = DataLoader(
            train_dataset,
            batch_size=BATCH_SIZE,
            sampler=train_sampler,
        )
    else:
        train_dataloader = DataLoader(
            train_dataset,
            batch_size=BATCH_SIZE,
            shuffle=True,
        )
    val_dataloader = None
    if val_split is not None:
        val_dataloader = DataLoader(
            val_split.dataset,
            batch_size=BATCH_SIZE,
            shuffle=False,
        )
    test_dataloader = DataLoader(
        test_split.dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
    )
    return train_dataloader, val_dataloader, test_dataloader, test_split


def run_epoch(model, dataloader, loss_fn, device, optimizer=None):
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_correct = 0
    total_examples = 0

    for images, labels in dataloader:
        images = images.to(device)
        labels = labels.to(device=device, dtype=torch.float32).unsqueeze(1)

        if training:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(training):
            logits = model(images)
            loss = loss_fn(logits, labels)
            if training:
                loss.backward()
                optimizer.step()

        batch_size = labels.size(0)
        total_loss += loss.item() * batch_size
        total_correct += ((logits >= 0) == (labels >= 0.5)).sum().item()
        total_examples += batch_size

    return total_loss / total_examples, total_correct / total_examples


def best_checkpoint_path(run_name: str) -> Path:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKPOINT_DIR / f"{run_name}_best.pt"


CHECKPOINT_CRITERIA = frozenset({"accuracy", "accuracy_minus_loss"})


def checkpoint_selection_score(
    accuracy: float,
    loss: float,
    *,
    criterion: str,
) -> float:
    """Higher score is better. Used to pick the best epoch checkpoint."""
    if criterion == "accuracy":
        return accuracy
    if criterion == "accuracy_minus_loss":
        return accuracy - loss
    raise ValueError(
        f"Unsupported checkpoint criterion {criterion!r}. "
        f"Choose from: {', '.join(sorted(CHECKPOINT_CRITERIA))}"
    )


def save_best_checkpoint(
    model: nn.Module,
    *,
    run_name: str,
    model_name: str,
    best_test_accuracy: float,
    best_epoch: int,
    best_test_loss: float | None = None,
    best_selection_accuracy: float | None = None,
    best_selection_loss: float | None = None,
    best_selection_split: str | None = None,
    checkpoint_criterion: str = "accuracy",
    best_selection_score: float | None = None,
) -> Path:
    checkpoint_path = best_checkpoint_path(run_name)
    payload = {
        "run_name": run_name,
        "model_name": model_name,
        "state_dict": model.state_dict(),
        "default_cfg": dict(model.default_cfg),
        "best_test_accuracy": best_test_accuracy,
        "best_epoch": best_epoch,
        "checkpoint_criterion": checkpoint_criterion,
        "forensic_channels": bool(getattr(model, "uses_forensic_channels", False)),
        "face_swap_recipe": bool(getattr(model, "face_swap_recipe", False)),
    }
    if payload["forensic_channels"]:
        payload["forensic_channel_order"] = FORENSIC_CHANNEL_ORDER
    if best_test_loss is not None:
        payload["best_test_loss"] = best_test_loss
    if best_selection_accuracy is not None:
        payload["best_selection_accuracy"] = best_selection_accuracy
    if best_selection_split is not None:
        payload["best_selection_split"] = best_selection_split
    if best_selection_loss is not None:
        payload["best_selection_loss"] = best_selection_loss
    if best_selection_score is not None:
        payload["best_selection_score"] = best_selection_score
    torch.save(payload, checkpoint_path)
    return checkpoint_path


def load_trained_model(
    run_name: str,
    *,
    model_name: str | None = None,
    device: torch.device | None = None,
) -> tuple[nn.Module, dict]:
    checkpoint_path = best_checkpoint_path(run_name)
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"No best checkpoint found: {checkpoint_path}")

    if device is None:
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    resolved_model_name = model_name or checkpoint["model_name"]
    if resolved_model_name == INCEPTION_MODEL_NAME or run_name.startswith(
        "inception_resnet_v1"
    ):
        return load_inception_resnet_v1_checkpoint(run_name, device=device)

    forensic_channels = bool(checkpoint.get("forensic_channels", False))
    saved_channel_order = checkpoint.get("forensic_channel_order")
    if forensic_channels and saved_channel_order is not None and tuple(
        saved_channel_order
    ) != FORENSIC_CHANNEL_ORDER:
        raise ValueError(
            "Checkpoint forensic channel order does not match this code version: "
            f"{saved_channel_order}"
        )
    model = create_model(
        resolved_model_name,
        forensic_channels=forensic_channels,
        face_swap_recipe=bool(checkpoint.get("face_swap_recipe", False)),
    )
    model.load_state_dict(checkpoint["state_dict"])
    model = model.to(device)
    return model, checkpoint


def _replace_module(root: nn.Module, module_path: str, replacement: nn.Module) -> None:
    path_parts = module_path.split(".")
    parent = root
    for part in path_parts[:-1]:
        parent = parent[int(part)] if part.isdigit() else getattr(parent, part)
    leaf = path_parts[-1]
    if leaf.isdigit():
        parent[int(leaf)] = replacement
    else:
        setattr(parent, leaf, replacement)


def _add_forensic_input_channels(model: nn.Module) -> None:
    first_conv_path, first_conv = next(
        (
            (name, module)
            for name, module in model.named_modules()
            if name and isinstance(module, nn.Conv2d) and module.in_channels == 3
        ),
        (None, None),
    )
    if first_conv is None:
        raise ValueError("Could not find a three-channel input convolution in the model")
    if first_conv.groups != 1:
        raise ValueError("Forensic input channels require an ungrouped input convolution")

    expanded_conv = nn.Conv2d(
        in_channels=FORENSIC_INPUT_CHANNELS,
        out_channels=first_conv.out_channels,
        kernel_size=first_conv.kernel_size,
        stride=first_conv.stride,
        padding=first_conv.padding,
        dilation=first_conv.dilation,
        groups=first_conv.groups,
        bias=first_conv.bias is not None,
        padding_mode=first_conv.padding_mode,
        device=first_conv.weight.device,
        dtype=first_conv.weight.dtype,
    )
    with torch.no_grad():
        expanded_conv.weight.zero_()
        expanded_conv.weight[:, :3].copy_(first_conv.weight)
        if first_conv.bias is not None:
            expanded_conv.bias.copy_(first_conv.bias)
    expanded_conv.weight.requires_grad_(first_conv.weight.requires_grad)
    if first_conv.bias is not None:
        expanded_conv.bias.requires_grad_(first_conv.bias.requires_grad)
    _replace_module(model, first_conv_path, expanded_conv)


def create_model(
    model_name,
    *,
    forensic_channels: bool = False,
    face_swap_recipe: bool = False,
):
    torch.manual_seed(SEED)
    if model_name not in SUPPORTED_TIMM_MODELS:
        supported = ", ".join(sorted(SUPPORTED_TIMM_MODELS))
        raise ValueError(
            f"Unsupported model {model_name!r}. Supported timm models: {supported}"
        )
    if forensic_channels and face_swap_recipe:
        raise ValueError("Choose either forensic channels or the RGB face-swap recipe")
    model = timm.create_model(model_name, pretrained=True, num_classes=1)
    if forensic_channels:
        _add_forensic_input_channels(model)
    model.classifier = _make_dense_head(model.classifier.in_features)
    model.uses_forensic_channels = forensic_channels
    model.face_swap_recipe = face_swap_recipe
    return model


def train_model(
    model,
    run_name,
    train_dataloader=None,
    test_dataloader=None,
    *,
    dataset_path: str | Path | None = None,
    model_name: str | None = None,
    epochs: int | None = None,
    learning_rate: float = 1e-3,
    weight_decay: float = 0.0,
    train_augmentation: bool = False,
    val_fraction: float = 0.0,
    supplement_celeb_train: bool = False,
    celeb_max_per_class: int = 750,
    supplement_kenjon_train: bool = False,
    kenjon_max_samples: int = 800,
    balance_train_sources: bool = True,
    checkpoint_on: str = "test",
    checkpoint_criterion: str = "accuracy",
):
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    model = model.to(device)

    if (train_dataloader is None) != (test_dataloader is None):
        raise ValueError("Pass both dataloaders or neither")
    val_dataloader = None
    test_split = None
    if train_dataloader is None:
        train_dataloader, val_dataloader, test_dataloader, test_split = build_dataloaders(
            model,
            dataset_path=dataset_path,
            train_augmentation=train_augmentation,
            val_fraction=val_fraction,
            supplement_celeb_train=supplement_celeb_train,
            celeb_max_per_class=celeb_max_per_class,
            supplement_kenjon_train=supplement_kenjon_train,
            kenjon_max_samples=kenjon_max_samples,
            balance_train_sources=balance_train_sources,
        )

    if checkpoint_on not in {"test", "val"}:
        raise ValueError("checkpoint_on must be 'test' or 'val'")
    if checkpoint_on == "val" and val_dataloader is None:
        raise ValueError("checkpoint_on='val' requires val_fraction > 0")
    if checkpoint_criterion not in CHECKPOINT_CRITERIA:
        raise ValueError(
            f"checkpoint_criterion must be one of {sorted(CHECKPOINT_CRITERIA)}, "
            f"got {checkpoint_criterion!r}"
        )

    total_epochs = epochs if epochs is not None else EPOCHS
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
        weight_decay=weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max(total_epochs, 1),
    )
    loss_fn = nn.BCEWithLogitsLoss()

    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    print(f"Model: {run_name} ({parameter_count / 1_000_000:.2f}M parameters)")
    print(f"Device: {device}", flush=True)
    print(
        f"Train examples: {len(train_dataloader.dataset)}, "
        f"test examples: {len(test_dataloader.dataset)}",
        flush=True,
    )
    if val_dataloader is not None:
        print(f"Validation examples: {len(val_dataloader.dataset)}", flush=True)
    selection_label = "val" if checkpoint_on == "val" else "test"
    print(
        f"Checkpoint selection: {selection_label} "
        f"criterion={checkpoint_criterion}",
        flush=True,
    )
    resolved_model_name = model_name or run_name
    train_losses, train_accuracies = [], []
    test_losses, test_accuracies = [], []
    val_losses, val_accuracies = [], []
    best_selection_accuracy = -1.0
    best_selection_loss = float("inf")
    best_selection_score = float("-inf")
    best_epoch = 0
    best_state_dict = None
    for episode in range(1, total_epochs + 1):
        train_loss, train_accuracy = run_epoch(
            model, train_dataloader, loss_fn, device, optimizer
        )
        test_loss, test_accuracy = float("nan"), float("nan")
        if checkpoint_on == "test":
            test_loss, test_accuracy = run_epoch(
                model, test_dataloader, loss_fn, device
            )
        val_loss, val_accuracy = float("nan"), float("nan")
        if val_dataloader is not None:
            val_loss, val_accuracy = run_epoch(
                model, val_dataloader, loss_fn, device
            )
            val_losses.append(val_loss)
            val_accuracies.append(val_accuracy)
        scheduler.step()
        train_losses.append(train_loss)
        train_accuracies.append(train_accuracy)
        if checkpoint_on == "test":
            test_losses.append(test_loss)
            test_accuracies.append(test_accuracy)
        selection_accuracy = val_accuracy if checkpoint_on == "val" else test_accuracy
        selection_loss = val_loss if checkpoint_on == "val" else test_loss
        selection_score = checkpoint_selection_score(
            selection_accuracy,
            selection_loss,
            criterion=checkpoint_criterion,
        )
        line = (
            f"Episode {episode:02d}/{total_epochs} | "
            f"train loss: {train_loss:.4f}, train accuracy: {train_accuracy:.2%}"
        )
        if checkpoint_on == "val":
            line += f" | val loss: {val_loss:.4f}, val accuracy: {val_accuracy:.2%}"
        else:
            line += f" | test loss: {test_loss:.4f}, test accuracy: {test_accuracy:.2%}"
        line += f" | lr: {scheduler.get_last_lr()[0]:.2e}"
        if checkpoint_criterion == "accuracy_minus_loss":
            line += f" | {selection_label} score: {selection_score:.4f}"
        print(line, flush=True)
        if selection_score > best_selection_score:
            best_selection_score = selection_score
            best_selection_accuracy = selection_accuracy
            best_selection_loss = selection_loss
            best_epoch = episode
            best_state_dict = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }

    if best_state_dict is not None:
        model.load_state_dict(best_state_dict)
        if checkpoint_on == "val":
            best_test_loss, best_test_accuracy = run_epoch(
                model, test_dataloader, loss_fn, device
            )
            print(
                f"Final held-out test | loss: {best_test_loss:.4f}, "
                f"accuracy: {best_test_accuracy:.2%}",
                flush=True,
            )
        else:
            best_test_loss = best_selection_loss
            best_test_accuracy = best_selection_accuracy
        checkpoint_path = save_best_checkpoint(
            model,
            run_name=run_name,
            model_name=resolved_model_name,
            best_test_accuracy=best_test_accuracy,
            best_epoch=best_epoch,
            best_test_loss=best_test_loss,
            best_selection_accuracy=best_selection_accuracy,
            best_selection_loss=best_selection_loss,
            best_selection_split=selection_label,
            checkpoint_criterion=checkpoint_criterion,
            best_selection_score=best_selection_score,
        )
        summary = (
            f"Best checkpoint (selected by {selection_label}, episode {best_epoch}, "
            f"selection accuracy {best_selection_accuracy:.2%}, "
            f"selection loss {best_selection_loss:.4f}; "
            f"held-out test accuracy {best_test_accuracy:.2%}, "
            f"loss {best_test_loss:.4f}"
        )
        if checkpoint_criterion == "accuracy_minus_loss":
            summary += f", score {best_selection_score:.4f}"
        summary += f") saved to {checkpoint_path}"
        print(summary, flush=True)

    episodes = range(1, total_epochs + 1)
    sns.set_theme(style="whitegrid")
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(episodes, train_losses, label="Train")
    if checkpoint_on == "val":
        axes[0].plot(episodes, val_losses, label="Validation")
    else:
        axes[0].plot(episodes, test_losses, label="Test")
    axes[0].set(title="Loss per Episode", xlabel="Episode", ylabel="Loss")
    axes[0].legend()
    axes[1].plot(episodes, train_accuracies, label="Train")
    if checkpoint_on == "val":
        axes[1].plot(episodes, val_accuracies, label="Validation")
    else:
        axes[1].plot(episodes, test_accuracies, label="Test")
    axes[1].set(title="Accuracy per Episode", xlabel="Episode", ylabel="Accuracy")
    axes[1].set_ylim(0, 1)
    axes[1].legend()
    figure.tight_layout()

    NEURAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    plot_path = NEURAL_RESULTS_DIR / f"{run_name}_training_results.png"
    figure.savefig(plot_path, dpi=150, bbox_inches="tight")
    print(f"Training plot saved to {plot_path}")
    plt.show()

    if test_split is not None:
        run_robustness_evaluation(
            model,
            test_split,
            loss_fn,
            device,
            run_name,
            NEURAL_RESULTS_DIR,
            batch_size=BATCH_SIZE,
        )


def main():
    model = create_model("mobilenetv3_large_100")
    train_model(model, "mobilenetv3_large", model_name="mobilenetv3_large_100")


if __name__ == "__main__":
    main()
