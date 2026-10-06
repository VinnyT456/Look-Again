"""Train a fresh EfficientNet-B0 on the matched face-cropped DF40 subset."""


from look_again.training import create_model, train_model


def main() -> None:
    model = create_model("efficientnet_b0", forensic_channels=True)
    train_model(
        model,
        "efficientnet_b0_facecrop",
        model_name="efficientnet_b0",
        epochs=30,
        learning_rate=1e-4,
        weight_decay=0.01,
        train_augmentation=True,
        val_fraction=0.12,
        checkpoint_on="val",
        checkpoint_criterion="accuracy_minus_loss",
    )


if __name__ == "__main__":
    main()
