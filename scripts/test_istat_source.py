"""Exercise request safety without making any network calls."""

import json
import hashlib
import fcntl
import time
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests

import istat_source

REAL_BOUNDED_HTTP = istat_source.bounded_http


class FakeClock:
    now = 1000.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class RetrievalSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.root = root
        self.clock = FakeClock()
        self.times = []
        self.status = 200
        self.failure = None
        self.duration = 0
        for mock in (
            patch("builtins.print"),  # Mocked GET diagnostics must not look like live traffic.
            patch.object(istat_source, "CACHE", root / "cache"),
            patch.object(istat_source, "LIMITER", root / "limiter.json"),
            patch.object(istat_source, "time", self.clock),
            patch.dict("os.environ", {"ISTAT_REFRESH": "1"}),
            patch.object(istat_source, "bounded_http", self.fake_send),
        ):
            mock.start()
            self.addCleanup(mock.stop)

    def fake_send(self, request, timeout):
        self.assertLessEqual(timeout, 45)
        self.times.append(self.clock.time())
        self.clock.sleep(self.duration)
        if self.failure:
            raise self.failure
        response = requests.Response()
        response.status_code = self.status
        response.url = request.url
        response.request = request
        response._content = b"saved data"
        if self.status == 429:
            response.headers["Retry-After"] = "86400"
        if self.status == 302:
            response.headers["Location"] = "https://demo.istat.it/next"
        return response

    def test_quiet_window_and_shared_rate_budget(self):
        for i in range(7):
            # Different sessions model separate notebook kernels/processes.
            istat_source.IstatSession().get(f"https://demo.istat.it/data/{i}")
        self.assertGreaterEqual(self.times[0], 1060)
        self.assertTrue(all(b - a >= 30 for a, b in zip(self.times, self.times[1:])))
        self.assertTrue(all(sum(0 <= t - p < 60 for p in self.times) <= 2 for t in self.times))

    def test_access_failure_stops_all_sessions(self):
        self.status = 429
        with self.assertRaisesRegex(RuntimeError, "Retry-After=86400"):
            istat_source.IstatSession().get("https://demo.istat.it/blocked")
        with self.assertRaisesRegex(RuntimeError, "no more calls"):
            istat_source.IstatSession().get("https://demo.istat.it/other")
        self.assertEqual(len(self.times), 1)
        self.assertTrue(json.loads(istat_source.LIMITER.read_text())["blocked"])

    def test_offline_requires_opt_in(self):
        with patch.dict("os.environ", {"ISTAT_REFRESH": ""}):
            with self.assertRaisesRegex(RuntimeError, "requires ISTAT_REFRESH=1"):
                istat_source.IstatSession().get("https://demo.istat.it/uncached")
        self.assertEqual(self.times, [])

    def test_redirect_is_not_followed(self):
        self.status = 302
        with self.assertRaisesRegex(RuntimeError, "redirect stopped"):
            istat_source.IstatSession().get("https://demo.istat.it/redirect")
        self.assertEqual(len(self.times), 1)

    def test_wrong_provider_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unexpected source host"):
            istat_source.IstatSession().get("https://example.com/")
        self.assertEqual(self.times, [])

    def test_same_day_matching_query_reuses_source(self):
        query = {"resource_id": "example", "key": {"REF_AREA": "IT"}}
        digest = hashlib.sha256(json.dumps(query, sort_keys=True).encode()).hexdigest()[:12]
        csv = self.root / f"example_{digest}.csv"
        csv.write_text("REF_AREA,TIME_PERIOD,value\nIT,2025,1.14\n")
        csv.with_suffix(".json").write_text("{}")
        with patch.object(istat_source, "SOURCES", self.root), patch.object(istat_source, "istat_client", side_effect=AssertionError("live retrieval")):
            self.assertEqual(istat_source.istat_data(**query).value.iloc[0], 1.14)
            with self.assertRaisesRegex(AssertionError, "live retrieval"):
                istat_source.istat_data("example", {"REF_AREA": "FR"})

    def test_previous_calendar_day_is_stale_even_within_24_hours(self):
        cached = self.root / "yesterday.csv"
        cached.write_text("data")
        midnight = datetime.now(istat_source.LOCAL_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
        stamp = (midnight - timedelta(seconds=1)).timestamp()
        os.utime(cached, (stamp, stamp))
        self.assertFalse(istat_source.cache_is_from_today(cached))

    def test_read_timeout_freezes_all_further_retrieval(self):
        self.failure = requests.ReadTimeout("stalled")
        with self.assertRaises(requests.ReadTimeout):
            istat_source.IstatSession().get("https://demo.istat.it/stall", timeout=9999)
        with patch.object(istat_source, "RUN_ID", "another-run"):
            with self.assertRaisesRegex(istat_source.IstatSafetyStop, "no more calls"):
                istat_source.IstatSession().get("https://demo.istat.it/next")
        self.assertEqual(len(self.times), 1)
        events = [json.loads(line) for line in istat_source.LIMITER.with_suffix(".jsonl").read_text().splitlines()]
        self.assertEqual([event["event"] for event in events], ["start", "finish"])
        self.assertIn("ReadTimeout", events[-1]["failure"])

    def test_spacing_starts_after_completion(self):
        self.duration = 5
        for i in range(2):
            istat_source.IstatSession().get(f"https://demo.istat.it/slow/{i}")
        self.assertGreaterEqual(self.times[1] - self.times[0], 35)

    def test_run_request_budget_cannot_be_reset_by_new_session(self):
        with patch.object(istat_source, "MAX_RUN_REQUESTS", 2):
            for i in range(2):
                istat_source.IstatSession().get(f"https://demo.istat.it/budget/{i}")
            with self.assertRaisesRegex(istat_source.IstatSafetyStop, "budget exhausted"):
                istat_source.IstatSession().get("https://demo.istat.it/budget/3")
        self.assertEqual(len(self.times), 2)

    def test_busy_lock_fails_without_queuing(self):
        with istat_source.LIMITER.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(istat_source.IstatSafetyStop, "no queued retrieval"):
                istat_source.IstatSession().get("https://demo.istat.it/busy")
        self.assertEqual(self.times, [])

    def test_no_metadata_needed_for_bounded_positional_query(self):
        self.assertEqual(istat_source.positional_key(
            "22_289_DF_DCIS_POPRES1_1",
            {"FREQ": "A", "REF_AREA": "IT", "DATA_TYPE": "JAN", "SEX": [], "AGE": [], "MARITAL_STATUS": "99"},
        ), "A.IT.JAN...99")
        with self.assertRaisesRegex(ValueError, "national Italy"):
            istat_source.positional_key("22_289_DF_DCIS_POPRES1_1", {})

    def test_total_deadline_kills_stalled_or_dripping_worker(self):
        # Genuine subprocess timeout; no sockets or external HTTP are involved.
        worker = self.root / "stuck_worker.py"
        worker.write_text("import sys,time\nwhile True:\n    print('drip', flush=True)\n    time.sleep(0.03)\n")
        request = requests.Request("GET", "https://demo.istat.it/stalled").prepare()
        started = time.monotonic()
        with patch.object(istat_source, "HTTP_WORKER", worker):
            with self.assertRaisesRegex(istat_source.IstatSafetyStop, "worker killed"):
                REAL_BOUNDED_HTTP(request, timeout=0.25)
        self.assertLess(time.monotonic() - started, 2)

    def test_oversized_transport_response_is_rejected(self):
        worker = self.root / "oversize_worker.py"
        worker.write_text("import json,base64\nprint(json.dumps({'status':200,'headers':{},'body':base64.b64encode(b'12345').decode()}))\n")
        request = requests.Request("GET", "https://demo.istat.it/oversize").prepare()
        with patch.object(istat_source, "HTTP_WORKER", worker), patch.object(istat_source, "MAX_RESPONSE_BYTES", 4):
            with self.assertRaisesRegex(istat_source.IstatSafetyStop, "size limit"):
                REAL_BOUNDED_HTTP(request, timeout=2)

    def test_legacy_requests_cannot_bypass_the_guard(self):
        with self.assertRaisesRegex(istat_source.IstatSafetyStop, "Unguarded ISTAT traffic disabled"):
            requests.get("https://sdmx.istat.it/legacy")
        self.assertEqual(self.times, [])

    def test_interruption_persists_the_halt(self):
        self.failure = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            istat_source.IstatSession().get("https://demo.istat.it/interrupted")
        with self.assertRaisesRegex(istat_source.IstatSafetyStop, "no more calls"):
            istat_source.IstatSession().get("https://demo.istat.it/after-interruption")
        self.assertEqual(len(self.times), 1)

    def test_total_run_budget_includes_the_quiet_window(self):
        with patch.object(istat_source, "MAX_RUN_SECONDS", 61):
            istat_source.IstatSession().get("https://demo.istat.it/run-budget/1")
            with self.assertRaisesRegex(istat_source.IstatSafetyStop, "budget exhausted"):
                istat_source.IstatSession().get("https://demo.istat.it/run-budget/2")
        self.assertEqual(len(self.times), 1)

    def test_worker_own_alarm_stops_dripping_without_parent_timeout(self):
        # Exercise the real worker and its OS alarm with a fake HTTP module.
        # There is no network access, including when the parent timeout is longer.
        fake = self.root / "requests.py"
        fake.write_text(
            "import time,types\n"
            "adapters=types.SimpleNamespace(HTTPAdapter=lambda **kwargs: None)\n"
            "class Reply:\n"
            "    headers={};status_code=200;is_redirect=False\n"
            "    def __enter__(self):return self\n"
            "    def __exit__(self,*args):pass\n"
            "    def iter_content(self,**kwargs):\n"
            "        while True:\n"
            "            time.sleep(.03)\n"
            "            yield b'drip'\n"
            "class Session:\n"
            "    def mount(self,*args):pass\n"
            "    def get(self,*args,**kwargs):return Reply()\n"
        )
        query = {"url": "https://demo.istat.it/fake", "headers": {}, "max_bytes": 1024,
                 "deadline": 0.25, "guard_pid": os.getpid(), "limiter_path": str(istat_source.LIMITER)}
        with istat_source.LIMITER.open("w+") as lock:
            json.dump({"active_request": {"pid": os.getpid(), "url": query["url"]}}, lock)
            lock.flush()
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            started = time.monotonic()
            result = subprocess.run(
                [sys.executable, str(istat_source.HTTP_WORKER)], input=json.dumps(query),
                text=True, capture_output=True, timeout=2,
                env={**os.environ, "PYTHONPATH": str(self.root)},
            )
        self.assertEqual(result.returncode, -14)  # SIGALRM, not an HTTP read timeout.
        self.assertLess(time.monotonic() - started, 1.5)

    def test_exact_user_authorized_probe_keeps_general_halt(self):
        url = "https://demo.istat.it/authorized-one"
        istat_source.LIMITER.write_text(json.dumps({
            "blocked": {"reason": "existing halt"},
            "authorized_probe": {"token": "one", "pid": os.getpid(), "url": url, "expires_at": 1200},
        }))
        istat_source.IstatSession(probe_token="one").get(url)
        state = json.loads(istat_source.LIMITER.read_text())
        self.assertEqual(state["blocked"], {"reason": "existing halt"})
        self.assertNotIn("authorized_probe", state)
        with self.assertRaisesRegex(istat_source.IstatSafetyStop, "no more calls"):
            istat_source.IstatSession().get("https://demo.istat.it/other")
        self.assertEqual(len(self.times), 1)

    def test_probe_permit_rejects_wrong_url_process_or_expiry(self):
        permit = {"token": "one", "pid": os.getpid(), "url": "https://demo.istat.it/one", "expires_at": 1200}
        for changed in ({"url": "https://demo.istat.it/another"}, {"pid": -1}, {"expires_at": 999}):
            istat_source.LIMITER.write_text(json.dumps({"blocked": {"reason": "halt"}, "authorized_probe": {**permit, **changed}}))
            with self.assertRaisesRegex(istat_source.IstatSafetyStop, "authorization"):
                istat_source.IstatSession(probe_token="one").get(permit["url"])
        self.assertEqual(self.times, [])


if __name__ == "__main__":
    unittest.main()
