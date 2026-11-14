"""Offline conditional period life expectancy for notebook 86."""

import numpy as np
import pandas as pd


def period_life_expectancy(probabilities):
    """Adult e_x by year, with uniform deaths within each year of age.

    Repeat the oldest available q at subsequent ages, closing the open tail
    analytically. This uses all single ages, including ages above 100.
    """
    q = probabilities.to_numpy(dtype=float)
    ages = probabilities.index
    if probabilities.empty or list(ages) != list(range(ages[0], ages[-1] + 1)):
        raise ValueError("Death probabilities require a complete single-age grid")
    if not probabilities.columns.is_unique:
        raise ValueError("Duplicate mortality years")
    if not np.isfinite(q).all() or ((q < 0) | (q > 1)).any():
        raise ValueError("Death probabilities must be finite and in [0, 1]")
    if (q[-1] <= 0).any():
        raise ValueError("The open oldest-age tail requires positive mortality")
    expectancy = np.empty_like(q)
    expectancy[-1] = 1 / q[-1] - 0.5
    for i in range(len(ages) - 2, -1, -1):
        expectancy[i] = 1 - q[i] / 2 + (1 - q[i]) * expectancy[i + 1]
    return pd.DataFrame(expectancy, index=ages, columns=probabilities.columns)


def expectancy_at_age(age, probabilities, expectancy):
    """Condition on survival to a fractional age under uniform deaths."""
    if not np.isfinite(age) or not probabilities.index.min() <= age <= probabilities.index.max():
        raise ValueError("Retirement age is outside the mortality age grid")
    integer_age = int(np.floor(age))
    fraction = age - integer_age
    q = probabilities.loc[integer_age]
    return (expectancy.loc[integer_age] - fraction + q * fraction**2 / 2) / (1 - q * fraction)


def retirement_expectancies(retirement, observed, projected):
    """Match retirement-year ages to that year's observed/projected life table."""
    if not observed.index.equals(projected.index):
        raise ValueError("Observed and projected mortality age grids differ")
    mortality = pd.concat([observed, projected], axis=1)
    if list(mortality.columns) != list(range(mortality.columns.min(), mortality.columns.max() + 1)):
        raise ValueError("Mortality years must be consecutive and nonoverlapping")
    if retirement.duplicated(["year", "scenario"]).any():
        raise ValueError("Duplicate retirement year/scenario")
    if not set(retirement.year) <= set(mortality.columns):
        raise ValueError("Missing mortality for a retirement year")
    expectancy = period_life_expectancy(mortality)
    result = retirement.copy()
    result["remaining_life_expectancy"] = [
        expectancy_at_age(row.retirement_age, mortality[row.year], expectancy[row.year])
        for row in result.itertuples()
    ]
    result["expected_age_at_death"] = result.retirement_age + result.remaining_life_expectancy
    result["mortality_source"] = np.where(result.year <= observed.columns.max(), "observed", "projected")
    return result
