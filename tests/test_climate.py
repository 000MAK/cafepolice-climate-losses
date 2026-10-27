import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from climate import fit_trend, parse_damage, predictive, rate  # noqa: E402


class ClimateTests(unittest.TestCase):
    def test_parse_damage_units(self):
        s = pd.Series(["10.00K", "1.5M", "2B", "0", None, "K", "250"])
        self.assertEqual(parse_damage(s).tolist(), [10_000.0, 1_500_000.0, 2e9, 0.0, 0.0, 0.0, 250.0])

    def test_trend_recovers_growth(self):
        rng = np.random.default_rng(3)
        years = np.arange(1996, 2026)
        counts = pd.Series(rng.poisson(500 * np.exp(0.03 * (years - 2010))), index=years)
        t = fit_trend(counts)
        self.assertAlmostEqual(t["b"], 0.03, delta=0.005)
        self.assertLess(t["annual_change_ci95"][0], 0.0305)
        self.assertAlmostEqual(float(rate(t, 2010)), 500, delta=25)

    def test_predictive_centres_on_trend(self):
        t = {"a": np.log(600), "b": 0.02, "b_se": 0.0, "dispersion": 5.0}
        sims = predictive(t, 2020, 100_000, np.random.default_rng(0))
        self.assertAlmostEqual(sims.mean(), 600 * np.exp(0.2), delta=6)


if __name__ == "__main__":
    unittest.main()
