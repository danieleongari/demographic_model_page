"""Offline weather completeness, cache and cohort-year regression checks."""

from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from heatwave_analysis import annual_heat_exposure, align_cohort_changes, correlations
import weather_source as weather


def daily(start, end, maximum=25):
    dates = pd.date_range(start, end)
    return pd.DataFrame({"time": dates, "temperature_2m_min": maximum - 10,
                         "temperature_2m_max": maximum})


class HeatwaveScience(unittest.TestCase):
    def test_cohort_column_matches_same_weather_year(self):
        annual = pd.DataFrame({"HeatWaveProxy": [10, 100, 20]}, index=pd.Index([2002, 2003, 2004], name="year"))
        ccr = pd.DataFrame({2002: [-0.1] * 15, 2003: [-0.3] * 15, 2004: [-0.2] * 15}, index=range(85, 100))
        result = align_cohort_changes(annual, ccr).set_index("year")
        self.assertAlmostEqual(result.at[2003, "cohort_decline"], 0.3)
        self.assertEqual(result.at[2003, "HeatWaveProxy"], 100)

    def test_cool_years_are_retained_as_zero_exposure(self):
        result = annual_heat_exposure(daily("2023-01-01", "2024-12-31"), 2023, 2024)
        self.assertEqual(list(result.index), [2023, 2024])
        self.assertEqual(result.HeatWaveProxy.tolist(), [0, 0])

    def test_missing_leap_day_is_rejected(self):
        frame = daily("2024-01-01", "2024-12-31")
        frame = frame.loc[frame.time != pd.Timestamp("2024-02-29")]
        with self.assertRaisesRegex(ValueError, "complete, unique"):
            annual_heat_exposure(frame, 2024, 2024)

    def test_signed_correlations_are_not_absolute_values(self):
        comparison = pd.DataFrame({"year": range(2002, 2008), "HeatWaveProxy": range(6),
                                   "cohort_decline": [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]})
        result = correlations(comparison)
        self.assertAlmostEqual(result.iloc[0].heat_vs_decline_spearman, -1)
        self.assertEqual(result.n_years.tolist(), [6, 6, 5])

    def test_partial_current_year_is_not_selected(self):
        period = weather.analysis_period(range(1952, 2027), now=datetime(2026, 11, 11, tzinfo=weather.ROME))
        self.assertEqual(period, (2002, 2025))


class WeatherCache(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.calls = 0
        for mock in (patch.object(weather, "CACHE", self.root),
                     patch.object(weather, "_fetch", self.fetch),
                     patch.dict(os.environ, {"WEATHER_REFRESH": "1"})):
            mock.start()
            self.addCleanup(mock.stop)

    def fetch(self, url):
        self.calls += 1
        params = parse_qs(urlparse(url).query)
        self.assertEqual(params["models"], ["era5"])
        frame = daily(params["start_date"][0], params["end_date"][0])
        payload = {"timezone": "Europe/Rome", "latitude": 45.5, "longitude": 9.25,
                   "daily_units": {"temperature_2m_min": "°C", "temperature_2m_max": "°C"},
                   "daily": {"time": frame.time.dt.strftime("%Y-%m-%d").tolist(),
                             "temperature_2m_min": frame.temperature_2m_min.tolist(),
                             "temperature_2m_max": frame.temperature_2m_max.tolist()}}
        return json.dumps(payload).encode()

    def test_matching_same_day_query_reuses_download(self):
        first, _ = weather.load_weather(2024, 2024)
        second, _ = weather.load_weather(2024, 2024)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(len(first), 366)
        self.assertEqual(self.calls, 1)

    def test_stale_query_is_refreshed_only_on_explicit_refresh(self):
        weather.load_weather(2024, 2024)
        payload = next(p for p in self.root.glob("*.json") if not p.name.endswith(".meta.json"))
        yesterday = payload.stat().st_mtime - 86400
        os.utime(payload, (yesterday, yesterday))
        with patch.dict(os.environ, {"WEATHER_REFRESH": ""}):
            weather.load_weather(2024, 2024)
        self.assertEqual(self.calls, 1)
        weather.load_weather(2024, 2024)
        self.assertEqual(self.calls, 2)

    def test_cached_content_hash_is_checked(self):
        weather.load_weather(2024, 2024)
        payload = next(p for p in self.root.glob("*.json") if not p.name.endswith(".meta.json"))
        payload.write_bytes(payload.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            weather.load_weather(2024, 2024)
        self.assertEqual(self.calls, 1)

    def test_missing_temperature_is_rejected(self):
        payload = json.loads(self.fetch("https://example.invalid/?models=era5&start_date=2024-01-01&end_date=2024-12-31"))
        payload["daily"]["temperature_2m_max"][20] = None
        with self.assertRaisesRegex(ValueError, "temperatures"):
            weather.validate_daily(payload, "2024-01-01", "2024-12-31")


if __name__ == "__main__":
    unittest.main()
