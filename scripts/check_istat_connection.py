"""One explicitly authorized connectivity check; the general live halt stays set.

Default is a dry run. --live authorizes one fixed national fertility observation,
not a refresh. Never retry this command after a failure in the same run.
"""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import time
import uuid
import xml.etree.ElementTree as ET

import requests

import istat_source as source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicitly authorize exactly one live request")
    args = parser.parse_args()
    dataset = "25_326_DF_DCIS_FECONDITA1_5"
    key = source.positional_key(dataset, {
        "FREQ": "A", "REF_AREA": "IT", "DATA_TYPE": "TOTFERR",
        "CITIZENSHIP": "TOTAL", "MOTHER_AGE": "TOTAL",
    })
    session = source.IstatSession(probe_token=uuid.uuid4().hex)
    request = session.prepare_request(requests.Request(
        "GET", f"https://esploradati.istat.it/SDMXWS/rest/data/{dataset}/{key}",
        params={"startPeriod": "2025", "endPeriod": "2025"},
        headers={"Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"},
    ))
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "url": request.url,
              "request_limit": 1, "hard_deadline_seconds": 20, "response_limit_bytes": 65536}
    if not args.live:
        print(json.dumps({**report, "mode": "dry run; no traffic"}, indent=2))
        return
    digest = hashlib.sha256((request.url + str(request.headers.get("Accept"))).encode()).hexdigest()
    cached = source.CACHE / f"{digest}.gz"
    if cached.exists() and source.cache_is_from_today(cached):
        raise source.IstatSafetyStop("This exact diagnostic response is already cached today; no repeat probe")
    source.MAX_REQUEST_SECONDS = 20
    source.MAX_RESPONSE_BYTES = 65536
    source.MAX_RUN_REQUESTS = 1
    source.MAX_RUN_SECONDS = 90
    os.environ["ISTAT_REFRESH"] = "1"
    token = session.probe_token
    with source.LIMITER.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock.seek(0)
        state = json.loads(lock.read() or "{}")
        state.setdefault("blocked", {"reason": "Connectivity-check-only session; normal retrieval remains halted", "at": time.time()})
        state["authorized_probe"] = {"token": token, "pid": os.getpid(), "url": request.url,
                                     "expires_at": time.time() + 120,
                                     "reason": "Explicit user request to safely check the current VPN connection"}
        lock.seek(0)
        lock.truncate()
        json.dump(state, lock)
    try:
        started = time.monotonic()
        response = session.send(request)
        root = ET.fromstring(response.content)
        values = [node.attrib["value"] for node in root.iter()
                  if node.tag.rsplit("}", 1)[-1] == "ObsValue"]
        if len(values) != 1:
            raise source.IstatSafetyStop(f"Expected one observation, got {len(values)}")
        report.update(status=response.status_code, bytes=len(response.content),
                      observation_count=len(values), value=float(values[0]),
                      elapsed_including_quiet_window_seconds=round(time.monotonic() - started, 3),
                      content_type=response.headers.get("Content-Type"), success=True)
    except Exception as error:
        report.update(success=False, error=f"{type(error).__name__}: {error}")
    finally:
        with source.LIMITER.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock.seek(0)
            state = json.loads(lock.read() or "{}")
            if state.get("authorized_probe", {}).get("token") == token:
                state.pop("authorized_probe")
            log = source.LIMITER.with_suffix(".jsonl")
            events = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            events = [event for event in events if event.get("run_id") == source.RUN_ID]
            report["live_attempts"] = sum(event["event"] == "start" for event in events)
            report["transport_events"] = events
            report["general_live_access_halted"] = bool(state.get("blocked"))
            lock.seek(0)
            lock.truncate()
            json.dump(state, lock)
        source.CACHE.mkdir(parents=True, exist_ok=True)
        (source.CACHE / "connectivity_check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
