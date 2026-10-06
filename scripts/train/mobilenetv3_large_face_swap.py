"""Train RGB-only MobileNetV3-Large on the existing DF40 face-crop dataset."""


from look_again.training import create_model, train_model
from look_again.df40_subset import LEGACY_FACE_CROP_DATASET_PATH


def main() -> None:
    model = create_model("mobilenetv3_large_100", face_swap_recipe=True)
    train_model(
        model,
        "mobilenetv3_large_existing_face_crops",
        model_name="mobilenetv3_large_100",
        dataset_path=LEGACY_FACE_CROP_DATASET_PATH,
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
