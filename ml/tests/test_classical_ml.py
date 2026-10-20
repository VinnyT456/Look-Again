import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from look_again.classical_ml.data import extract_image_collection, extract_split_features
from look_again.classical_ml.ensemble import select_voting_weights
from look_again.classical_ml.evaluation import evaluate_model, save_confusion_matrix
from look_again.classical_ml.features import FeatureConfig
from look_again.classical_ml.inference import load_model_bundle, predict_image
from look_again.classical_ml.models import get_model, xgboost_available
from look_again.classical_ml.training import _grouped_cv_splits, train_model


def sample_images(count=12):
    images = []
    labels = []
    for index in range(count):
        label = index % 2
        pixels = np.zeros((24, 24, 3), dtype=np.uint8)
        pixels[:] = 35 if label == 0 else 220
        pixels[::3, :, 0] = (index * 11 + 40) % 256
        pixels[:, ::4, 2] = (index * 7 + 90) % 256
        images.append(Image.fromarray(pixels))
        labels.append(label)
    return images, np.asarray(labels, dtype=np.int64)


class ClassicalPipelineTests(unittest.TestCase):
    def test_confusion_matrix_plot_is_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "confusion.png"
            save_confusion_matrix(
                np.asarray([[3, 1], [0, 4]]),
                ("fake", "real"),
                output,
                "test",
            )
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    def test_feature_cache_round_trip_uses_split_manifest(self):
        images, labels = sample_images(count=1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_path = root / "sample.png"
            images[0].save(image_path)
            base_dataset = SimpleNamespace(
                root=str(root),
                samples=[(str(image_path), int(labels[0]))],
            )
            split = SimpleNamespace(
                dataset=SimpleNamespace(dataset=base_dataset, indices=[0]),
                group_ids=("identity-a",),
                class_names=("fake", "real"),
            )
            first = extract_split_features(
                split,
                "train",
                FeatureConfig(features=("lbp",)),
                cache_dir=root / "cache",
            )
            second = extract_split_features(
                split,
                "train",
                FeatureConfig(features=("lbp",)),
                cache_dir=root / "cache",
            )
            np.testing.assert_array_equal(first.X, second.X)
            np.testing.assert_array_equal(first.y, second.y)
            self.assertEqual(len(list((root / "cache").glob("train_*.npz"))), 1)

    def test_image_to_features_to_train_predict_and_persist(self):
        images, labels = sample_images()
        config = FeatureConfig()
        data = extract_image_collection(images, labels, config)
        self.assertEqual(data.X.shape, (12, 79))
        self.assertEqual(data.y.shape, (12,))

        train_indices = np.arange(8)
        test_indices = np.arange(8, 12)
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "logistic.joblib"
            result = train_model(
                "logistic",
                data.X[train_indices],
                data.y[train_indices],
                data.X[test_indices],
                data.y[test_indices],
                class_names=("real", "fake"),
                feature_config=config,
                feature_name_list=data.feature_names,
                artifact_path=artifact,
            )
            self.assertTrue(artifact.is_file())
            self.assertEqual(len(result.model.predict(data.X[test_indices])), 4)
            bundle = load_model_bundle(artifact)
            prediction = predict_image(bundle, images[8])
            self.assertIn(prediction["predicted_label"], {"real", "fake"})
            self.assertAlmostEqual(sum(prediction["probabilities"].values()), 1.0, places=5)
            scaler_mean = result.model.named_steps["scale"].mean_
            np.testing.assert_allclose(scaler_mean, data.X[train_indices].mean(axis=0))
            metrics = evaluate_model(
                result.model,
                data.X[test_indices],
                data.y[test_indices],
                ("real", "fake"),
                model_name="logistic",
            )
            self.assertEqual(len(metrics["confusion_matrix"]), 2)
            self.assertIn("fake", metrics["per_class"])
            self.assertIsNotNone(result.validation_metrics)

    def test_hard_voting_factory_fits_multiple_classifiers(self):
        images, labels = sample_images()
        data = extract_image_collection(images, labels, FeatureConfig(features=("lbp", "dct")))
        model = get_model(
            "hard_voting",
            {"members": ["logistic", "decision_tree"]},
            random_state=42,
        )
        model.fit(data.X[:8], data.y[:8])
        self.assertEqual(model.predict(data.X[8:]).shape, (4,))

    def test_random_forest_and_svm_fit_with_probability_outputs(self):
        images, labels = sample_images()
        data = extract_image_collection(images, labels, FeatureConfig(features=("lbp",)))
        models = (
            get_model("random_forest", {"n_estimators": 8, "n_jobs": 1}),
            get_model("svm"),
        )
        for model in models:
            model.fit(data.X[:8], data.y[:8])
            self.assertEqual(model.predict_proba(data.X[8:]).shape, (4, 2))

    def test_weighted_soft_voting_uses_validation_candidates(self):
        images, labels = sample_images()
        data = extract_image_collection(images, labels, FeatureConfig(features=("lbp",)))
        candidates = {
            "logistic": get_model("logistic"),
            "decision_tree": get_model("decision_tree"),
        }
        for model in candidates.values():
            model.fit(data.X[:8], data.y[:8])
        weights = select_voting_weights(
            candidates,
            data.X[8:],
            data.y[8:],
            [
                {"logistic": 1.0, "decision_tree": 1.0},
                {"logistic": 0.7, "decision_tree": 0.3},
            ],
        )
        model = get_model(
            "weighted_soft_voting",
            {"members": ["logistic", "decision_tree"], "weights": weights},
        )
        model.fit(data.X[:8], data.y[:8])
        self.assertEqual(model.predict_proba(data.X[8:]).shape, (4, 2))

    def test_stacking_model_trains_with_identity_grouped_oof_predictions(self):
        images, labels = sample_images()
        data = extract_image_collection(images, labels, FeatureConfig(features=("lbp",)))
        result = train_model(
            "stacking",
            data.X[:10],
            data.y[:10],
            config={"members": ["logistic", "decision_tree"], "cv": 5},
            groups=data.group_ids[:10],
            class_names=("real", "fake"),
        )
        self.assertEqual(result.model.predict(data.X[10:]).shape, (2,))

    def test_grouped_stacking_splits_keep_identity_groups_intact(self):
        X = np.arange(40, dtype=np.float32).reshape(20, 2)
        y = np.asarray([0, 1] * 10)
        groups = np.asarray([f"identity-{index}" for index in range(20)])
        splits = _grouped_cv_splits(X, y, groups, folds=5, random_state=42)
        self.assertEqual(len(splits), 5)
        for train_indices, held_out_indices in splits:
            self.assertFalse(set(groups[train_indices]) & set(groups[held_out_indices]))

    @unittest.skipIf(xgboost_available(), "XGBoost is installed")
    def test_missing_xgboost_has_install_instruction(self):
        with self.assertRaisesRegex(ImportError, "uv sync --extra xgboost"):
            get_model("xgboost")

    @unittest.skipUnless(xgboost_available(), "Optional XGBoost is not installed")
    def test_xgboost_binary_model_fits_and_predicts_probabilities(self):
        images, labels = sample_images()
        data = extract_image_collection(images, labels, FeatureConfig(features=("lbp", "dct")))
        model = get_model(
            "xgboost",
            {"n_estimators": 5, "max_depth": 2},
            random_state=42,
            num_classes=2,
        )
        self.assertEqual(model.get_params()["n_jobs"], 1)
        self.assertEqual(model.get_params()["tree_method"], "exact")
        model.fit(data.X[:8], data.y[:8])
        self.assertEqual(model.predict(data.X[8:]).shape, (4,))
        self.assertEqual(model.predict_proba(data.X[8:]).shape, (4, 2))

    @unittest.skipUnless(xgboost_available(), "Optional XGBoost is not installed")
    def test_xgboost_multiclass_objective_uses_class_count(self):
        model = get_model("xgboost", {"n_estimators": 1, "n_jobs": 1}, num_classes=3)
        self.assertEqual(model.get_params()["objective"], "multi:softprob")
        self.assertEqual(model.get_params()["num_class"], 3)


if __name__ == "__main__":
    unittest.main()
