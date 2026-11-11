"""Pure, offline transformations for notebook 53."""

import numpy as np
import pandas as pd


def annual_heat_exposure(daily, start_year, end_year):
    dates = pd.DatetimeIndex(daily.time)
    expected = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31")
    if not dates.equals(expected):
        raise ValueError("Annual exposure requires complete, unique daily dates")
    result = daily.assign(
        year=dates.year,
        HeatWaveProxy=(daily.temperature_2m_max - 30).clip(lower=0),
        days_above_30=(daily.temperature_2m_max > 30).astype(int),
    ).groupby("year")[["HeatWaveProxy", "days_above_30"]].sum()
    assert list(result.index) == list(range(start_year, end_year + 1))
    return result


def align_cohort_changes(annual, ccr, min_age=85, max_age=99):
    """CCR column y already denotes Jan y → Jan y+1: do not shift weather years."""
    ccr = ccr.rename(columns=int)
    selected = ccr.loc[min_age:max_age]
    if list(selected.index) != list(range(min_age, max_age + 1)):
        raise ValueError("Incomplete cohort age range")
    mean = selected.mean(axis=0).rename("mean_ccr")
    mean.index.name = "year"
    result = annual.join(mean, how="left")
    if not np.isfinite(result.to_numpy()).all():
        raise ValueError("Missing cohort/weather overlap")
    result["cohort_decline"] = -result.mean_ccr
    return result.reset_index()


def correlations(comparison):
    rows = []
    for label, excluded in (("All complete years", []), ("Exclude 2020–2021", [2020, 2021]),
                            ("Also exclude 2003", [2003, 2020, 2021])):
        sample = comparison.loc[~comparison.year.isin(excluded)]
        if len(sample) < 3:
            raise ValueError("At least three years are required")
        rows.append({"sample": label, "n_years": len(sample),
                     "heat_vs_decline_spearman": sample.HeatWaveProxy.corr(sample.cohort_decline, method="spearman"),
                     "year_vs_decline_spearman": sample.year.corr(sample.cohort_decline, method="spearman")})
    return pd.DataFrame(rows)


def age_sensitivity(annual, ccr):
    rows = []
    for age in range(50, 100):
        stats = correlations(align_cohort_changes(annual, ccr, age))
        rows.append({"minimum_age": age, "age_group": f"{age}–99",
                     "heat_exposure": stats.iloc[1].heat_vs_decline_spearman,
                     "calendar_year": stats.iloc[1].year_vs_decline_spearman,
                     "heat_without_2003": stats.iloc[2].heat_vs_decline_spearman})
    return pd.DataFrame(rows)
