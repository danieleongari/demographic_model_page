"""Analytical and independent survival-sum checks; no network access."""

import unittest

import numpy as np
import pandas as pd

from retiree_life_expectancy import expectancy_at_age, period_life_expectancy, retirement_expectancies


class ConditionalLifeExpectancy(unittest.TestCase):
    def test_constant_mortality_has_analytical_geometric_expectancy(self):
        q = pd.DataFrame({2025: [0.2] * 60}, index=range(60, 120))
        np.testing.assert_allclose(period_life_expectancy(q), 4.5)

    def test_certain_death_and_zero_mortality_years(self):
        q = pd.DataFrame({2025: [0, 0, 1]}, index=[60, 61, 62])
        np.testing.assert_allclose(period_life_expectancy(q)[2025], [2.5, 1.5, 0.5])

    def test_matches_independent_forward_survival_sum(self):
        q = pd.DataFrame({2025: [0.05, 0.1, 0.3, 0.6]}, index=range(60, 64))
        e = period_life_expectancy(q)
        annual_q = np.r_[q[2025].to_numpy(), np.repeat(0.6, 100)]
        survival = np.r_[1, np.cumprod(1 - annual_q)]
        expected = ((survival[:-1] + survival[1:]) / 2).sum()
        self.assertAlmostEqual(e.at[60, 2025], expected)
        # Unconditional expectancy minus age ignores survival to that age.
        self.assertGreater(e.at[61, 2025], e.at[60, 2025] - 1)

    def test_fractional_age_conditions_on_survival_within_year(self):
        q = pd.DataFrame({2025: [0.2, 0.4]}, index=[60, 61])
        e = period_life_expectancy(q)
        # At 60.5: 0.9 survive; 0.425 person-years until 61, then
        # 0.8 * e_61 person-years. Divide by the 0.9 survivors.
        self.assertAlmostEqual(expectancy_at_age(60.5, q[2025], e[2025]), (0.425 + 0.8 * 2) / 0.9)
        self.assertEqual(expectancy_at_age(60, q[2025], e[2025]), e.at[60, 2025])

    def test_lower_mortality_increases_remaining_life(self):
        q = pd.DataFrame({2025: [0.1, 0.2, 0.5], 2026: [0.05, 0.1, 0.25]}, index=range(60, 63))
        e = period_life_expectancy(q)
        self.assertTrue((e[2026] > e[2025]).all())

    def test_year_specific_mortality_and_nine_retirement_ages(self):
        observed = pd.DataFrame({2025: [0.1, 0.2, 0.5]}, index=range(60, 63))
        projected = pd.DataFrame({2026: [0.05, 0.1, 0.25]}, index=range(60, 63))
        retirement = pd.DataFrame([
            {"year": year, "scenario": str(s), "retirement_age": 60 + s / 8}
            for year in [2025, 2026] for s in range(9)
        ])
        result = retirement_expectancies(retirement, observed, projected)
        self.assertEqual(len(result), 18)
        self.assertEqual(result.groupby("year").scenario.nunique().tolist(), [9, 9])
        self.assertEqual(result.mortality_source.unique().tolist(), ["observed", "projected"])
        fixed_age = result.query("scenario == '0'").remaining_life_expectancy
        self.assertGreater(fixed_age.iloc[1], fixed_age.iloc[0])

    def test_invalid_and_incomplete_inputs_fail(self):
        for values, ages in [([0.1, np.nan], [60, 61]), ([0.1, 1.1], [60, 61]),
                             ([0.1, 0], [60, 61]), ([0.1, 0.2], [60, 62])]:
            with self.subTest(values=values, ages=ages), self.assertRaises(ValueError):
                period_life_expectancy(pd.DataFrame({2025: values}, index=ages))
        q = pd.DataFrame({2025: [0.1, 0.2]}, index=[60, 61])
        e = period_life_expectancy(q)
        with self.assertRaises(ValueError):
            expectancy_at_age(59, q[2025], e[2025])
        retirement = pd.DataFrame({"year": [2027], "scenario": ["a"], "retirement_age": [60]})
        with self.assertRaisesRegex(ValueError, "Missing mortality"):
            retirement_expectancies(retirement, q, q.rename(columns={2025: 2026}))


if __name__ == "__main__":
    unittest.main()
