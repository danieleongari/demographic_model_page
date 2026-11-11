# ISTAT retrieval audit — 11 November 2026

The original refresh serialized requests and enforced a 15.1-second gap between
attempt starts. That alone was insufficient protection against a hanging service.

Findings from the local cache and execution output:

- SDMX dictionary keys triggered an implicit `dataflow/...?...references=all`
  request before each data query, retrieving full structures and codelists.
- A 180-second Requests timeout bounded individual connection/read waits, not
  total elapsed time. A response dripping bytes could continue much longer.
- A historical-series request timed out and was manually retried once. A timeout
  did not freeze later clients. This behavior has been removed.
- Only a rolling 60 seconds of start timestamps was retained. Cache mtimes record
  completion, so they cannot retrospectively certify the whole rolling request
  rate. There is no evidence sufficient to claim that the full earlier run
  stayed within the public-IP limit, or that a provider block caused the stall.
- The final successful ISTAT source download completed at **09:03:03 CET**; model
  initial validation completed at **09:06:50 CET**. The subsequently interrupted tool was
  the browser-preview check, after the ISTAT downloads had finished.

The revised transport, tested without contacting ISTAT:

- A quiet minute per live run, a shared nonblocking lock, and **30.1 seconds from
  response completion to the next start**: at most two requests per rolling
  minute through this helper. A busy lock fails immediately.
- A killable subprocess with a **45-second total deadline**, including DNS/TLS
  and slow body transfer; 5-second connection and 10-second read timeouts;
  **8 MiB** maximum body size, checked during streaming. The worker has an
  independent termination alarm and verifies its parent's active limiter lock.
- At most **eight attempts and eight minutes** per run. No redirects or retries.
  Any error, timeout, cancellation, unexpected SDMX content or budget/size failure
  persists a halt shared across sessions. Switching run IDs does not clear it.
- Reviewed positional keys for the seven national queries remove implicit
  metadata requests. Unknown dataflows/dimensions and unrestricted geography are
  rejected. All seven cached wire responses replayed to identical tidy data with
  one response each and zero metadata calls.
- Plain Requests/legacy `istatapi` traffic to ISTAT is rejected once the guard is
  loaded. Supplementary notebooks `20` and `25` load it before legacy imports;
  their saved outputs were retained, without live execution.
- Persistent JSONL start/finish events include URLs, times, durations, status and
  failures. They live alongside the shared limiter in the OS temporary directory.
  Raw downloads and their query manifests remain gitignored.

Live access was left **halted as a precaution** after the user's report. Do not
clear this state or send a test/probe request during this run. Cached analysis
continues to work. Other users/devices sharing the public IP must still be
coordinated separately; a local limiter cannot account for their traffic.

## Subsequent user-authorized VPN connectivity check

On 11 November 2026 the user explicitly requested a safe check after enabling
an Italy-based Surfshark VPN. This new authorization was limited to a single
national fertility observation for 2025. An expiring permit matched the exact
URL and calling process and was consumed without clearing the general halt.
The check had a 20-second total deadline and 64 KiB response cap, with a quiet
minute first and no metadata calls, redirects or retries.

At 10:07 CET, exactly one live attempt succeeded: HTTP 200 in 4.793 seconds,
1,577 response bytes, one observation (2025 total fertility rate: 1.14). Local
routing showed an `ipsec0` tunnel. This demonstrates current connectivity for
that small query; there was no original-connection control test to attribute
recovery to the VPN. The general halt remains set. The response and diagnostic
report are cached locally and gitignored; the model was not rerun.

## Subsequent continuation and standing recovery preference

The user then explicitly authorized continuing the task and requested that agents
ask them to turn on the VPN if future ISTAT requests block or hang. This preference
is recorded in `copilot-instructions.md`: stop traffic, ask the user to enable or
check their VPN, wait for confirmation, then make one guarded connection check.
Never switch VPN exits or repeatedly retry automatically, and preserve provider
limits, deadlines and any explicit `Retry-After`.

The successful check plus explicit continuation provided authorization to review
and clear the precautionary local halt under the shared lock. Its prior value
was archived in the limiter state and audit log; counters were retained. All
remaining verification used cached inputs, with no additional ISTAT calls.
