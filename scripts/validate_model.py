"""Offline scientific checks for the national demographic dependency chain."""

from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
from scipy.special import expit

from istat_source import ROOT, SOURCES


def matrix(name):
    return pd.read_csv(ROOT / "data" / name, index_col=0).rename(columns=int)


def validate():
    pop = matrix("pop_by_age_year.csv")
    mortality = matrix("deathprob_by_age_year.csv")
    future_mortality = matrix("deathprob_by_age_year_proj.csv")
    migration = matrix("average_migration_balance.csv").iloc[:, 0]
    model = pd.read_csv(ROOT / "data" / "pop_by_age_year_proj.csv")
    fertility = json.loads((ROOT / "data" / "fertility_fitted.json").read_text())
    scenarios = [c for c in model if c.startswith("migr ")]
    first, last = min(pop.columns), max(pop.columns)
    assert list(pop.index) == list(range(101)), "Population age grid must be 0–100+"
    assert list(pop.columns) == list(range(first, last + 1)), "Missing population years"
    assert len(scenarios) == 9 and not model.duplicated(["year", "AGE"]).any()
    assert list(model.columns[:2]) == ["year", "AGE"]
    assert model.groupby("year").AGE.apply(list).apply(lambda ages: sorted(ages) == list(range(101))).all()
    assert set(model.year) == set(range(first, 2101))
    for label, values in (("population", pop), ("model", model[scenarios]), ("migration", migration)):
        assert np.isfinite(values.to_numpy()).all(), f"Nonfinite {label}"
        assert (values.to_numpy() >= 0).all(), f"Negative {label}"
    for probabilities in (mortality, future_mortality):
        assert np.isfinite(probabilities.to_numpy()).all()
        assert ((probabilities >= 0) & (probabilities <= 1)).all().all()
    assert set(range(last, 2100)) <= set(future_mortality.columns), "Missing mortality for forecast transitions"
    assert fertility["last_observed_year"] == last - 1
    assert fertility["last_official_year"] >= 2025

    # Source uniqueness, release vintage, official uncertainty ordering and sex totals.
    source_summary = []
    for manifest in sorted(SOURCES.glob("*.json")):
        info = json.loads(manifest.read_text())
        frame = pd.read_csv(manifest.with_suffix(".csv"), dtype=str)
        assert not frame.duplicated([c for c in frame if c != "value"]).any()
        import hashlib

        assert hashlib.sha256(manifest.with_suffix(".csv").read_bytes()).hexdigest() == info["csv_sha256"]
        if "resource_id" not in info:
            if info.get("kind", "").startswith("retained"):
                source_summary.append({k: info[k] for k in ("kind", "git_commit", "source_notebook", "time_min", "time_max")})
            continue
        dataset = info["resource_id"]
        if "PREVDEM1" in dataset:
            assert int(frame.TIME_PERIOD.min()) >= 2025, "Stale ISTAT projection vintage"
            table = frame.assign(value=pd.to_numeric(frame.value)).pivot(index="TIME_PERIOD", columns="FORECAST_INTERVAL", values="value")
            assert (table.PROJLOW80 <= table.PROJMED).all() and (table.PROJMED <= table.PROJUPP80).all()
            assert int(frame.TIME_PERIOD.max()) == 2080
        if "POPRES" in dataset:
            table = frame.assign(value=pd.to_numeric(frame.value)).pivot(index=["TIME_PERIOD", "AGE"], columns="SEX", values="value")
            assert (table["1"] + table["2"] == table["9"]).all(), f"Sex totals mismatch in {dataset}"
        if "FECONDITA1_5" in dataset:
            official = frame.query("CITIZENSHIP == 'TOTAL'").sort_values("TIME_PERIOD").iloc[-1]
            assert fertility["last_official_year"] == int(official.TIME_PERIOD)
            assert fertility["last_official_value"] == float(official.value)
        source_summary.append({k: info[k] for k in ("resource_id", "time_min", "time_max", "retrieved_at")})

    # Reconcile historical cohort changes and migration using origin-age mortality.
    changes = matrix("cc_by_age_year.csv")
    residuals = []
    for year in changes.columns:
        expected = pop[year + 1] - pop[year].shift(1)
        np.testing.assert_array_equal(changes[year], expected.loc[changes.index])
        if year >= 2002 and year in mortality.columns and year not in (2020, 2021):
            residuals.append((expected + (pop[year] * mortality[year]).shift(1)).loc[1:80].clip(lower=0))
    expected_migration = pd.concat(residuals, axis=1).mean(axis=1).astype(int)
    np.testing.assert_array_equal(migration, expected_migration)

    # Every scenario must preserve all observed age/year values exactly.
    max_cohort_error = 0.0
    max_birth_error = 0.0
    for scenario in scenarios:
        projection = model.pivot(index="AGE", columns="year", values=scenario)
        np.testing.assert_array_equal(projection.loc[:, first:last], pop)
        migration_factor = 2 if "double" in scenario else 0 if "zero" in scenario else 1
        target = 2 if "↑" in scenario else 0 if "↓" in scenario else fertility["last_observed_value"]
        for year in range(last + 1, 2101):
            previous = projection[year - 1]
            q = future_mortality[year - 1]
            expected = previous.loc[0:99].to_numpy() * (1 - q.loc[0:99].to_numpy())
            expected[-1] += previous.loc[100] * 0.6
            expected[:80] += migration.to_numpy() * migration_factor
            error = np.abs(projection.loc[1:100, year].to_numpy() - expected).max()
            max_cohort_error = max(max_cohort_error, float(error))
            assert error <= 2, f"Cohort accounting failed: {scenario}, {year}, {error}"
            t = year - 1
            fraction = (t - fertility["last_observed_year"]) / (2100 - fertility["last_observed_year"])
            rate = fertility["last_observed_value"] + fraction * (target - fertility["last_observed_value"])
            cdf = expit(fertility["sigmoid_k"] * (np.arange(17, 51) - np.polyval(fertility["sigmoid_x0"], t)))
            cdf = (cdf - cdf[0]) / (cdf[-1] - cdf[0])
            births = np.dot(previous.loc[18:50], np.diff(cdf)) * fertility["assumed_women_ratio"] * rate
            error = abs(projection.loc[0, year] - births)
            max_birth_error = max(max_birth_error, float(error))
            assert error <= 2, f"Birth accounting failed: {scenario}, {year}"

    baseline = pd.read_csv(StringIO(subprocess.check_output(
        ["git", "show", "HEAD:data/pop_by_age_year_proj.csv"], cwd=ROOT, text=True
    )))
    current_totals = model.groupby("year")[scenarios].sum()
    previous_totals = baseline.groupby("year")[scenarios].sum()
    retirement = json.loads((ROOT / "data" / "retirement_summary.json").read_text())
    assert set(retirement["scenarios"]) == set(scenarios), "Incomplete 1990-cohort retirement results"
    comparisons = {}
    for year in (last, 2050, 2080, 2100):
        comparisons[str(year)] = {
            scenario: {"population": int(current_totals.at[year, scenario]),
                       "change_from_previous_model": int(current_totals.at[year, scenario] - previous_totals.at[year, scenario])}
            for scenario in scenarios
        }
    return {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "observation_years": [first, last],
        "mortality_observed_through": int(max(mortality.columns)),
        "fertility": fertility,
        "retirement_1990_cohort": retirement,
        "average_annual_migration": int(migration.sum()),
        "max_cohort_rounding_error_people": max_cohort_error,
        "max_birth_rounding_error_people": max_birth_error,
        "checks": ["source hashes and unique keys", "complete age/year grids", "sex totals",
                   "nonnegative finite populations", "probabilities in [0, 1]", "historical cohort changes",
                   "migration reconciliation", "observations preserved in all nine scenarios",
                   "yearly births/deaths/migration accounting", "base-2025 official projections and ordered intervals"],
        "source_snapshots": source_summary,
        "scenario_totals_and_changes": comparisons,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
