from look_again.training import create_model, train_model


def main():
    model = create_model("mobilenetv3_small_100")
    train_model(
        model,
        "mobilenetv3_small",
        model_name="mobilenetv3_small_100",
    )


if __name__ == "__main__":
    main()
