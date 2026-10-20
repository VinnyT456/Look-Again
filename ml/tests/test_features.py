import unittest

import numpy as np
from PIL import Image

from look_again.classical_ml.features import (
    FeatureConfig,
    extract_dct_features,
    extract_ela_features,
    extract_features,
    extract_features_with_names,
    extract_lbp_features,
    extract_noise_features,
    feature_family_slices,
    feature_names,
)


class FeatureExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(42)
        cls.rgb = rng.integers(0, 256, size=(48, 64, 3), dtype=np.uint8)
        cls.image = Image.fromarray(cls.rgb)
        cls.gray = Image.fromarray(cls.rgb[..., 0])

    def assert_finite_shape(self, values, length):
        self.assertEqual(values.shape, (length,))
        self.assertTrue(np.isfinite(values).all())

    def test_lbp_is_fixed_size_normalized_histogram(self):
        values = extract_lbp_features(self.gray)
        self.assert_finite_shape(values, 10)
        self.assertAlmostEqual(float(values.sum()), 1.0, places=6)
        self.assertGreaterEqual(float(values.min()), 0.0)

    def test_ela_has_fixed_statistics_for_rgb_and_grayscale(self):
        self.assert_finite_shape(extract_ela_features(self.image), 24)
        self.assert_finite_shape(extract_ela_features(self.gray), 24)

    def test_dct_is_fixed_and_constant_image_is_finite(self):
        self.assert_finite_shape(extract_dct_features(self.image), 12)
        constant = np.full((16, 16), 127, dtype=np.uint8)
        self.assert_finite_shape(extract_dct_features(constant), 12)

    def test_noise_is_fixed_and_finite(self):
        self.assert_finite_shape(extract_noise_features(self.image), 33)
        self.assert_finite_shape(extract_noise_features(self.gray), 33)

    def test_combined_vector_order_dimension_and_ablation(self):
        vector, names = extract_features_with_names(self.image)
        self.assertEqual(vector.dtype, np.float32)
        self.assertEqual(len(vector), 79)
        self.assertEqual(names, feature_names())
        self.assertTrue(np.isfinite(vector).all())
        np.testing.assert_array_equal(vector, extract_features(self.image))

        config = FeatureConfig(features=("noise", "lbp"))
        names_for_subset = feature_names(config)
        self.assertEqual(names_for_subset[0], "lbp_bin_00")
        self.assertEqual(len(names_for_subset), 43)
        self.assertEqual(
            set(feature_family_slices(config)), {"lbp", "noise"}
        )
        self.assertEqual(len(extract_features(self.gray, config)), 43)


if __name__ == "__main__":
    unittest.main()
