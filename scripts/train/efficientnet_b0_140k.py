"""Train EfficientNet-B0 on the 140K real-vs-fake baseline (no DF40 / supplements)."""

from look_again.dataset_140k import resolve_140k_dataset_root
from look_again.training import create_model, train_model


def main() -> None:
    dataset_root = resolve_140k_dataset_root()
    model = create_model("efficientnet_b0")
    train_model(
        model,
        "efficientnet_b0_140k",
        model_name="efficientnet_b0",
        dataset_path=dataset_root,
        epochs=30,
        learning_rate=1e-4,
        weight_decay=0.01,
        train_augmentation=True,
        val_fraction=0.0,
        supplement_celeb_train=False,
        supplement_kenjon_train=False,
        balance_train_sources=False,
        checkpoint_on="val",
        checkpoint_criterion="accuracy_minus_loss",
    )


if __name__ == "__main__":
    main()
