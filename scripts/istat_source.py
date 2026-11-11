"""Cached ISTAT retrieval. Live access is opt-in with ISTAT_REFRESH=1.

Every HTTP request (including SDMX's implicit structure queries) uses one
cross-process limiter. No retries or automatic redirects are permitted.
"""

import fcntl
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import pandas as pd
import numpy as np
import requests
import sdmx

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources"
CACHE = ROOT / ".cache" / "istat"
# Shared by every checkout/kernel under this OS account, rather than per notebook.
LIMITER = Path(tempfile.gettempdir()) / "demographic-model-istat-limiter.json"
INTERVAL = 30.1
MAX_REQUEST_SECONDS = 45
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_RUN_REQUESTS = 8
MAX_RUN_SECONDS = 480
RUN_ID = os.environ.get("ISTAT_RUN_ID") or uuid.uuid4().hex
HTTP_WORKER = Path(__file__).with_name("istat_http_worker.py")
DATA_DIMENSIONS = {
    "22_289_DF_DCIS_POPRES1_1": ("FREQ", "REF_AREA", "DATA_TYPE", "SEX", "AGE", "MARITAL_STATUS"),
    "26_295_DF_DCIS_MORTALITA1_2": ("FREQ", "REF_AREA", "DATA_TYPE", "SEX", "AGE"),
    "25_326_DF_DCIS_FECONDITA1_5": ("FREQ", "REF_AREA", "DATA_TYPE", "CITIZENSHIP", "MOTHER_AGE"),
    "25_326_DF_DCIS_FECONDITA1_7": ("FREQ", "REF_AREA", "DATA_TYPE", "CITIZENSHIP", "MOTHER_AGE"),
    "165_889_DF_DCIS_PREVDEM1_1": ("FREQ", "REF_AREA", "DATA_TYPE", "FORECAST_INTERVAL", "AGE", "SEX"),
    "165_889_DF_DCIS_PREVDEM1_3": ("FREQ", "REF_AREA", "DATA_TYPE", "FORECAST_INTERVAL", "AGE", "SEX"),
    "28_185": ("FREQ", "REF_AREA", "DATA_TYPE", "CHANGE_OF_RESIDENCE", "CITIZENSHIP", "SEX", "AGE", "TERRITORY_NEXT_RESID", "COUNTRY_PREV_RESID", "COUNTRY_NEXT_RESID"),
}
LOCAL_TIMEZONE = ZoneInfo("Europe/Rome")


def cache_is_from_today(path):
    return datetime.fromtimestamp(path.stat().st_mtime, LOCAL_TIMEZONE).date() == datetime.now(LOCAL_TIMEZONE).date()


class IstatSafetyStop(RuntimeError):
    """Stop all live retrieval after a failure, hang or safety-budget violation."""


def bounded_http(request, timeout):
    """The child cannot keep this caller waiting by slowly dripping response bytes."""
    query = {"url": request.url,
             "headers": {k: v for k, v in request.headers.items() if k.lower() in ("accept", "accept-encoding", "user-agent")},
             "max_bytes": MAX_RESPONSE_BYTES, "deadline": timeout,
             "guard_pid": os.getpid(), "limiter_path": str(LIMITER)}
    try:
        with subprocess.Popen(
            [sys.executable, str(HTTP_WORKER)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ) as worker:
            try:
                output, _stderr = worker.communicate(json.dumps(query), timeout=timeout)
            except BaseException:
                worker.kill()
                worker.communicate()
                raise
            if worker.returncode:
                raise IstatSafetyStop("ISTAT transport failed; no retry")
    except subprocess.TimeoutExpired as error:
        raise IstatSafetyStop(f"ISTAT total request deadline exceeded ({timeout:.1f}s); worker killed") from error
    result = json.loads(output)
    if "error" in result:
        raise IstatSafetyStop(result["error"])
    response = requests.Response()
    response.status_code = result["status"]
    response.headers.update(result["headers"])
    response.url, response.request = request.url, request
    response._content = base64.b64decode(result["body"])
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise IstatSafetyStop("ISTAT response exceeds the size limit")
    return response


def positional_key(resource_id, key):
    """Use known dimension order, avoiding SDMX's implicit references=all calls."""
    dimensions = DATA_DIMENSIONS.get(resource_id)
    if dimensions is None or set(key) - set(dimensions):
        raise ValueError("Unreviewed ISTAT dataflow/dimensions; add a bounded query explicitly")
    area = key.get("REF_AREA")
    if area != "IT" and not (resource_id == "28_185" and set(area or []) == {"IT", "ITTOT"}):
        raise ValueError("Unbounded geography: national Italy filters are required")
    def codes(value):
        return "+".join(sorted(map(str, value))) if isinstance(value, (list, tuple)) else str(value)
    return ".".join(codes(key.get(dimension, "")) for dimension in dimensions)


class IstatSession(requests.Session):
    def __init__(self, *, probe_token=None):
        super().__init__()
        self.urls = []
        self.probe_token = probe_token

    def send(self, request, **kwargs):
        host = urlparse(request.url).hostname or ""
        if host != "istat.it" and not host.endswith(".istat.it"):
            raise ValueError(f"Unexpected source host: {host}")
        if request.method != "GET":
            raise ValueError("Only reviewed public GET requests are supported")
        self.urls.append(request.url)
        digest = hashlib.sha256((request.url + str(request.headers.get("Accept"))).encode()).hexdigest()
        CACHE.mkdir(parents=True, exist_ok=True)
        payload, meta = CACHE / f"{digest}.gz", CACHE / f"{digest}.json"
        if payload.exists() and meta.exists() and (
            os.environ.get("ISTAT_REFRESH") != "1" or cache_is_from_today(payload)
        ):
            info = json.loads(meta.read_text())
            response = requests.Response()
            response.status_code, response.url, response.request = 200, request.url, request
            response.headers.update(info["headers"])
            response._content = gzip.decompress(payload.read_bytes())
            return response
        if os.environ.get("ISTAT_REFRESH") != "1":
            raise RuntimeError("Live ISTAT access requires ISTAT_REFRESH=1; use saved source CSVs offline.")

        with LIMITER.open("a+") as state_file:
            try:
                fcntl.flock(state_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise IstatSafetyStop("Another ISTAT request holds the lock; no queued retrieval") from error
            state_file.seek(0)
            state = json.loads(state_file.read() or "{}")
            permit = state.get("authorized_probe", {})
            authorized = (
                self.probe_token is not None
                and permit.get("token") == self.probe_token
                and permit.get("pid") == os.getpid()
                and permit.get("url") == request.url
                and permit.get("expires_at", 0) > time.time()
            )
            if self.probe_token is not None and not authorized:
                raise IstatSafetyStop("Single-request authorization is absent, expired, or does not match")
            if state.get("blocked") and not authorized:
                raise IstatSafetyStop("ISTAT retrieval halted after a failure; no more calls until explicitly reviewed")
            if authorized:
                # Consume one exact-URL/process permit; keep the global halt set.
                state.pop("authorized_probe")

            def save_state():
                state_file.seek(0)
                state_file.truncate()
                json.dump(state, state_file)
                state_file.flush()

            def audit(event):
                with LIMITER.with_suffix(".jsonl").open("a") as log:
                    log.write(json.dumps(event) + "\n")

            now = time.time()
            runs = state.setdefault("runs", {})
            run = runs.setdefault(RUN_ID, {"started": now, "attempts": 0, "quiet_until": now + 60})
            # Keep a bounded recent run ledger; attempt events remain in the log.
            state["runs"] = {k: v for k, v in runs.items() if now - v["started"] < 172800}
            stamps = state.get("requests", [])
            recent = [t for t in stamps if now - t < 60]
            earliest = max(run["quiet_until"], state.get("last_completed", 0) + INTERVAL,
                           stamps[-1] + INTERVAL if stamps else 0)
            if len(recent) >= 5:
                earliest = max(earliest, recent[-5] + 60.1)
            delay = max(0, earliest - now)
            if authorized and now + delay >= permit["expires_at"]:
                save_state()
                raise IstatSafetyStop("Single-request authorization expires before the quiet window ends")
            if run["attempts"] >= MAX_RUN_REQUESTS or now + delay - run["started"] >= MAX_RUN_SECONDS:
                state["blocked"] = {"reason": "refresh budget exhausted", "at": now}
                save_state()
                raise IstatSafetyStop("ISTAT refresh budget exhausted; no retry or further calls")
            save_state()
            if delay:
                print(f"ISTAT shared limiter: waiting {delay:.1f}s", flush=True)
                time.sleep(delay)
            started = time.time()
            run["attempts"] += 1
            state["requests"] = [t for t in stamps if started - t < 60] + [started]
            state["active_request"] = {"url": request.url, "started": started, "pid": os.getpid()}
            save_state()
            audit({"event": "start", "run_id": RUN_ID, "url": request.url, "at": started})
            print(f"ISTAT GET {request.url} (total deadline {MAX_REQUEST_SECONDS}s)", flush=True)
            response, failure = None, None
            try:
                remaining = MAX_RUN_SECONDS - (started - run["started"])
                response = bounded_http(request, min(MAX_REQUEST_SECONDS, remaining))
                body = response.content[:20000].lower()
                if response.status_code in (401, 403, 429) or any(
                    phrase in body for phrase in (b"access denied", b"too many requests", b"accesso negato", b"access blocked")
                ):
                    raise IstatSafetyStop(f"ISTAT access stopped: HTTP {response.status_code}; Retry-After={response.headers.get('Retry-After')}")
                if response.is_redirect:
                    raise IstatSafetyStop("ISTAT redirect stopped; no automatic follow-up request")
                response.raise_for_status()
                if "/SDMXWS/rest/" in request.url and "xml" not in response.headers.get("Content-Type", "").lower():
                    raise IstatSafetyStop("Unexpected non-XML SDMX response; possible service/block page")
            except BaseException as error:
                failure = f"{type(error).__name__}: {error}"
                state["blocked"] = {"reason": failure, "at": time.time(),
                                    "retry_after": response.headers.get("Retry-After") if response is not None else None}
                raise
            finally:
                finished = time.time()
                state["last_completed"] = finished
                state.pop("active_request", None)
                save_state()
                audit({"event": "finish", "run_id": RUN_ID, "url": request.url,
                       "at": finished, "duration_seconds": finished - started,
                       "status": response.status_code if response is not None else None, "failure": failure})
            payload.write_bytes(gzip.compress(response.content))
            meta.write_text(json.dumps({"url": request.url, "headers": dict(response.headers),
                                       "started_at": started, "completed_at": finished}, indent=2))
            return response


def istat_client():
    return sdmx.Client("ISTAT", session=IstatSession())


def istat_data(resource_id, key):
    """Return tidy SDMX data, preserving dimension codes as strings in the cache."""
    query = {"resource_id": resource_id, "key": key}
    digest = hashlib.sha256(json.dumps(query, sort_keys=True).encode()).hexdigest()[:12]
    stem = f"{resource_id}_{digest}"
    csv = SOURCES / f"{stem}.csv"
    manifest = SOURCES / f"{stem}.json"
    if os.environ.get("ISTAT_REFRESH") != "1" or (csv.exists() and manifest.exists() and cache_is_from_today(csv)):
        if not csv.exists():
            raise FileNotFoundError(f"Missing source snapshot {csv.name}; refresh explicitly with ISTAT_REFRESH=1.")
        result = pd.read_csv(csv, dtype=str)
        result["value"] = pd.to_numeric(result["value"])
        return result
    client = istat_client()
    result = sdmx.to_pandas(client.data(resource_id=resource_id, key=positional_key(resource_id, key))).reset_index()
    if result.empty or result["value"].isna().any():
        raise ValueError(f"Empty/incomplete ISTAT result: {resource_id}")
    SOURCES.mkdir(parents=True, exist_ok=True)
    result.to_csv(csv, index=False)
    manifest.write_text(json.dumps({
        **query,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "time_min": str(result.TIME_PERIOD.min()),
        "time_max": str(result.TIME_PERIOD.max()),
        "rows": len(result),
        "requests": client.session.urls,
        "csv_sha256": hashlib.sha256(csv.read_bytes()).hexdigest(),
    }, indent=2) + "\n")
    return result


def install_istat_guard():
    """Reject legacy requests clients that bypass the guarded ISTAT transport."""
    original = requests.Session.send
    if getattr(original, "_istat_guard", False):
        return

    def guarded_send(session, request, **kwargs):
        host = urlparse(request.url).hostname or ""
        if host == "istat.it" or host.endswith(".istat.it"):
            raise IstatSafetyStop("Unguarded ISTAT traffic disabled; use istat_data() or the cached runner")
        return original(session, request, **kwargs)

    guarded_send._istat_guard = True
    requests.Session.send = guarded_send


def worldbank_fertility():
    """Historical comparison only; never substitute this for current ISTAT TFR."""
    csv = SOURCES / "worldbank_fertility_ITA.csv"
    refresh = os.environ.get("ISTAT_REFRESH") == "1" and (not csv.exists() or not cache_is_from_today(csv))
    if refresh:
        import wbgapi as wb

        SOURCES.mkdir(parents=True, exist_ok=True)
        series = wb.data.DataFrame("SP.DYN.TFRT.IN", "ITA").T.dropna()["ITA"]
        series.index = [int(year[-4:]) for year in series.index]
        series.rename_axis("year").rename("value").sort_index().to_csv(csv)
    if csv.exists() and (refresh or not csv.with_suffix(".json").exists()):
        csv.with_suffix(".json").write_text(json.dumps({
            "indicator": "SP.DYN.TFRT.IN", "country": "ITA",
            "source": "https://api.worldbank.org/v2/country/ITA/indicator/SP.DYN.TFRT.IN",
            "retrieved_at": datetime.fromtimestamp(csv.stat().st_mtime, timezone.utc).isoformat(),
            "csv_sha256": hashlib.sha256(csv.read_bytes()).hexdigest(),
        }, indent=2) + "\n")
    return pd.read_csv(csv, index_col="year")["value"]


def population_history():
    """Retain the checked-in pre-2019 baseline, including its saved sex split.

    Historical reconstruction endpoints need not be queried for each current-data
    refresh. The saved notebook figure contains the full historical series; check
    it against the existing population matrix before creating a local cache.
    This is a retained baseline, not a newly retrieved ISTAT observation.
    """
    csv = SOURCES / "retained_population_history.csv"
    if not csv.exists():
        notebook_path = "notebooks/14_investigate_italian_residents.ipynb"
        original = json.loads(subprocess.check_output(["git", "show", f"HEAD:{notebook_path}"], cwd=ROOT))
        figure = next(
            output["data"]["application/vnd.plotly.v1+json"]
            for cell in original["cells"] for output in cell.get("outputs", [])
            if "frames" in output.get("data", {}).get("application/vnd.plotly.v1+json", {})
        )

        def array(values):
            return np.frombuffer(base64.b64decode(values["bdata"]), dtype=values["dtype"]) if isinstance(values, dict) else values

        rows = []
        for frame in figure["frames"]:
            year = int(frame["name"])
            if year >= 2019:
                continue
            for trace in frame["data"]:
                for age, value in zip(array(trace["x"]), array(trace["y"])):
                    rows.append({"FREQ": "A", "REF_AREA": "IT", "DATA_TYPE": "JAN",
                                 "AGE": f"Y{age}" if age < 100 else "Y_GE100",
                                 "SEX": {"M": "1", "F": "2", "T": "9"}[trace["name"]],
                                 "TIME_PERIOD": str(year), "value": int(value)})
        result = pd.DataFrame(rows)
        baseline = pd.read_csv(ROOT / "data" / "pop_by_age_year.csv", index_col=0).rename(columns=int)
        totals = result.query("SEX == '9'").assign(age=lambda f: f.AGE.str.extract(r"(\d+)").astype(int))
        retained = totals.pivot(index="age", columns="TIME_PERIOD", values="value").rename(columns=int).sort_index()
        np.testing.assert_array_equal(retained, baseline.loc[:, retained.columns])
        SOURCES.mkdir(parents=True, exist_ok=True)
        result.to_csv(csv, index=False)
        csv.with_suffix(".json").write_text(json.dumps({
            "kind": "retained checked-in historical baseline; not a new download",
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_notebook": notebook_path,
            "time_min": int(retained.columns.min()), "time_max": int(retained.columns.max()),
            "csv_sha256": hashlib.sha256(csv.read_bytes()).hexdigest(),
        }, indent=2) + "\n")
    result = pd.read_csv(csv, dtype=str)
    result["value"] = pd.to_numeric(result["value"])
    return result


install_istat_guard()
