"""Internal single-request transport, launched under its provider's shared lock.

The parent enforces a killable wall-clock deadline including DNS, TLS and body
transfer. Do not invoke this worker directly to retrieve data.
"""

import base64
import json
import fcntl
import os
from pathlib import Path
import signal
import sys

def main():
    query = json.load(sys.stdin)
    try:
        # Also terminate if the parent is interrupted or killed during retrieval.
        signal.setitimer(signal.ITIMER_REAL, query["deadline"])
        if os.getppid() != query["guard_pid"]:
            raise RuntimeError("Transport requires its guarded parent process")
        with Path(query["limiter_path"]).open() as guard:
            state = json.load(guard)
            active = state.get("active_request", {})
            if active.get("pid") != query["guard_pid"] or active.get("url") != query["url"]:
                raise RuntimeError("No matching guarded request")
            try:
                fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise RuntimeError("Transport requires the shared limiter lock")
        import requests

        session = requests.Session()
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=0))
        with session.get(
            query["url"], headers=query["headers"], allow_redirects=False,
            timeout=(5, 10), stream=True,
        ) as response:
            limit = query["max_bytes"]
            if int(response.headers.get("Content-Length", 0)) > limit:
                raise ValueError(f"Response exceeds {limit} bytes")
            body = bytearray()
            if response.status_code not in (401, 403, 429) and not response.is_redirect:
                for chunk in response.iter_content(chunk_size=65536):
                    body.extend(chunk)
                    if len(body) > limit:
                        raise ValueError(f"Decoded response exceeds {limit} bytes")
            result = {"status": response.status_code, "headers": dict(response.headers),
                      "body": base64.b64encode(body).decode("ascii")}
    except Exception as error:
        result = {"error": f"{type(error).__name__}: {error}"}
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
