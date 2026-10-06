
from look_again.paths import PROJECT_ROOT

from look_again.training import create_model, load_trained_model, train_model


def main():
    model = create_model("efficientnet_b0")
    checkpoint_path = PROJECT_ROOT / "checkpoints" / "efficientnet_b0_best.pt"
    if checkpoint_path.is_file():
        model, checkpoint = load_trained_model("efficientnet_b0")
        print(
            f"Fine-tuning from {checkpoint_path.name} "
            f"(episode {checkpoint['best_epoch']}, "
            f"prior selection accuracy {checkpoint['best_test_accuracy']:.2%})",
            flush=True,
        )

    train_model(
        model,
        "efficientnet_b0",
        epochs=10,
        learning_rate=1e-4,
        weight_decay=0.01,
        train_augmentation=True,
        val_fraction=0.12,
        supplement_celeb_train=True,
        celeb_max_per_class=350,
        supplement_kenjon_train=True,
        kenjon_max_samples=800,
        balance_train_sources=True,
        checkpoint_on="val",
        checkpoint_criterion="accuracy_minus_loss",
    )


if __name__ == "__main__":
    main()
