"""Daily ERA5 temperatures via Open-Meteo, cached locally and opt-in to refresh.

Use six-year chunks, at least 31.1s apart after completion. Long date ranges
count as multiple provider calls; at most two such chunks/minute stay below
the free API's weighted limit. No API key is needed for noncommercial use.
"""

from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "sources" / "open_meteo"
LIMITER = Path(tempfile.gettempdir()) / "demographic-model-open-meteo-limiter.json"
WORKER = Path(__file__).with_name("istat_http_worker.py")
ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
ROME = ZoneInfo("Europe/Rome")
RUN_ID = uuid.uuid4().hex
INTERVAL = 31.1
DEADLINE = 45
MAX_BYTES = 2 * 1024 * 1024


def analysis_period(columns, now=None):
    """Preserve the original 2002 start and use only complete, available years."""
    available = sorted(map(int, columns))
    cutoff = (now or datetime.now(ROME)).date() - timedelta(days=6)
    start, end = 2002, min(max(available), cutoff.year - 1)
    if start > end or not set(range(start, end + 1)) <= set(available):
        raise ValueError("Incomplete demographic years for the heatwave comparison")
    return start, end


def validate_daily(payload, start_date, end_date):
    if payload.get("error"):
        raise ValueError(f"Open-Meteo error: {payload.get('reason')}")
    if payload.get("timezone") != "Europe/Rome":
        raise ValueError("Unexpected weather timezone")
    for variable in ("temperature_2m_min", "temperature_2m_max"):
        if payload.get("daily_units", {}).get(variable) != "°C":
            raise ValueError(f"Unexpected units for {variable}")
    frame = pd.DataFrame(payload["daily"])
    frame["time"] = pd.to_datetime(frame["time"])
    expected = pd.date_range(start_date, end_date, freq="D")
    if not pd.DatetimeIndex(frame.time).equals(expected):
        raise ValueError("Missing, duplicated, or unordered weather dates")
    values = frame[["temperature_2m_min", "temperature_2m_max"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values[:, 0] > values[:, 1]).any():
        raise ValueError("Missing or inconsistent daily temperatures")
    return frame


def _fetch(url):
    """One provider request, through a shared lock and killable transport."""
    with LIMITER.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock.seek(0)
        state = json.loads(lock.read() or "{}")
        if state.get("blocked"):
            raise RuntimeError("Open-Meteo retrieval halted after a failure; review before retrying")

        def save():
            lock.seek(0)
            lock.truncate()
            json.dump(state, lock)
            lock.flush()

        run = state.setdefault("runs", {}).setdefault(RUN_ID, {"started": time.time(), "attempts": 0})
        delay = max(0, state.get("last_completed", 0) + INTERVAL - time.time())
        if run["attempts"] >= 8 or time.time() + delay - run["started"] >= 480:
            raise RuntimeError("Open-Meteo retrieval budget exhausted")
        if delay:
            print(f"Open-Meteo limiter: waiting {delay:.1f}s", flush=True)
            time.sleep(delay)
        started = time.time()
        deadline = min(DEADLINE, 480 - (started - run["started"]))
        run["attempts"] += 1
        state["active_request"] = {"pid": os.getpid(), "url": url, "started": started}
        save()
        query = {"url": url, "headers": {"Accept": "application/json"},
                 "max_bytes": MAX_BYTES, "deadline": deadline,
                 "guard_pid": os.getpid(), "limiter_path": str(LIMITER)}
        failure, status = None, None
        print(f"Open-Meteo GET {url} (total deadline {DEADLINE}s)", flush=True)
        try:
            with subprocess.Popen([sys.executable, str(WORKER)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as child:
                try:
                    output, _stderr = child.communicate(json.dumps(query), timeout=deadline)
                except BaseException:
                    child.kill()
                    child.communicate()
                    raise
                if child.returncode:
                    raise RuntimeError("Open-Meteo transport failed; no retry")
            result = json.loads(output)
            if "error" in result:
                raise RuntimeError(result["error"])
            status = result["status"]
            if status != 200:
                raise RuntimeError(f"Open-Meteo HTTP {status}; Retry-After={result['headers'].get('Retry-After')}; no retry")
            import base64

            content = base64.b64decode(result["body"])
            if len(content) > MAX_BYTES:
                raise ValueError("Open-Meteo response exceeds 2 MiB")
            payload = json.loads(content)
            if payload.get("error"):
                raise ValueError(f"Open-Meteo error: {payload.get('reason')}")
            return content
        except BaseException as error:
            failure = f"{type(error).__name__}: {error}"
            state["blocked"] = {"reason": failure, "at": time.time()}
            raise
        finally:
            state["last_completed"] = time.time()
            state.pop("active_request", None)
            save()
            with LIMITER.with_suffix(".jsonl").open("a") as log:
                log.write(json.dumps({"url": url, "started": started, "completed": state["last_completed"],
                                      "status": status, "failure": failure}) + "\n")


def load_weather(start_year, end_year):
    """Return complete daily data and provenance; no HTTP in ordinary notebook runs."""
    frames, manifests = [], []
    for first in range(start_year, end_year + 1, 6):
        last = min(first + 5, end_year)
        params = {"latitude": 45.464664, "longitude": 9.188540,
                  "start_date": f"{first}-01-01", "end_date": f"{last}-12-31",
                  "daily": "temperature_2m_min,temperature_2m_max", "models": "era5",
                  "timezone": "Europe/Rome", "temperature_unit": "celsius"}
        query = {"endpoint": ENDPOINT, "params": params}
        digest = hashlib.sha256(json.dumps(query, sort_keys=True).encode()).hexdigest()[:16]
        path = CACHE / f"era5_milan_{digest}.json"
        meta = path.with_suffix(".meta.json")
        today = path.exists() and datetime.fromtimestamp(path.stat().st_mtime, ROME).date() == datetime.now(ROME).date()
        if os.environ.get("WEATHER_REFRESH") == "1" and not today:
            content = _fetch(ENDPOINT + "?" + urlencode(params))
            payload = json.loads(content)
            validate_daily(payload, params["start_date"], params["end_date"])
            CACHE.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            meta.write_text(json.dumps({**query, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                                       "sha256": hashlib.sha256(content).hexdigest(),
                                       "returned_grid": {k: payload.get(k) for k in ("latitude", "longitude", "elevation")},
                                       "attribution": "ERA5 reanalysis via Open-Meteo; CC BY 4.0"}, indent=2) + "\n")
        if not path.exists() or not meta.exists():
            raise FileNotFoundError("Missing weather cache; run scripts/refresh_model.py --heatwaves --refresh")
        content, manifest = path.read_bytes(), json.loads(meta.read_text())
        if manifest["endpoint"] != ENDPOINT or manifest["params"] != params or hashlib.sha256(content).hexdigest() != manifest["sha256"]:
            raise ValueError("Weather cache query/hash mismatch")
        frames.append(validate_daily(json.loads(content), params["start_date"], params["end_date"]))
        manifests.append(manifest)
    frame = pd.concat(frames, ignore_index=True)
    if not pd.DatetimeIndex(frame.time).equals(pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31")):
        raise ValueError("Incomplete combined weather coverage")
    return frame, {"start_year": start_year, "end_year": end_year, "days": len(frame),
                   "model": "ERA5", "timezone": "Europe/Rome", "queries": manifests}
