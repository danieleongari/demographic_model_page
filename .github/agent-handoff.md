# Current agent handoff

- **Status, 2026-11-11:** The national-model refresh and supplementary notebook 53
  update are complete. Notebook 53 uses complete 2002–2025 weather/cohort years;
  four bounded Open-Meteo requests succeeded without an API key. No additional
  ISTAT requests were made. No commit or deployment was requested.
- **Standing user preference:** If an actual ISTAT API request blocks or hangs,
  stop traffic and ask the user to turn on their VPN (Surfshark, Italy), or to
  check/reconnect it if already enabled. Explain that their confirmation permits
  one tiny guarded connectivity check; do not ask a redundant second permission.
  Respect explicit `Retry-After`, wait a quiet minute, and stop if that check fails.
  Do not switch VPN exits or retry automatically. This replaces earlier blanket
  guidance against requesting a VPN change. Distinguish remote failures from a
  local halt flag, which alone is not a reason to ask for VPN activation.
- The user-authorized VPN check at 10:07 CET made exactly one metadata-free
  request: HTTP 200 in 4.793 seconds, 1,577 bytes, one national 2025 TFR observation
  (1.14). System routing used `ipsec0`. VPN causality is unproven because there
  was no original-connection control test. After explicit user continuation, the
  precautionary halt was reviewed and cleared under the shared lock; its old
  value was archived and request counters/audit history retained. The connection
  check's one-use authorization was consumed. No additional live calls followed.
- Maintained notebook chain: cached catalogue cells of `00`, then `14`, `30`,
  `40`, `45`, `63`, `70`, `73`, `84`, executed in order with HTTP disabled. Figures,
  notebook HTML and `index.html` were updated. Supplementary `20`/`25` preserve
  historical outputs and block unguarded legacy ISTAT calls. The rest of `00`
  remains optional exploration. Notebook `53` is now refreshed separately with
  `python scripts/refresh_model.py --heatwaves --refresh` (Open-Meteo only), or
  `--heatwaves` for offline execution; it is not a national-model prerequisite.
- Inputs: residents through 1 January 2026; mortality and final fertility through
  2025; ISTAT base-2025 population/fertility projections through 2080. Official
  2025 TFR is 1.14; calibrated effective model rate is 1.10972919. The provisional
  January–July 2026 estimate stays separate. Pre-2019 population was retained from
  the checked-in notebook figure and verified against the population matrix.
- Model fixes: consistent fitted fertility weights for ages 18–50; migration
  residuals aligned with origin-age mortality; mortality's recent-average window
  uses the latest 12 available non-COVID years. Original nine scenarios and the
  assumed 40% mortality for 100+ remain. The 2100 scenarios span 16.6–77.5 million;
  the 1990 cohort's demographic retirement proxy spans ages 67–72 (2057–2062),
  with reference population ratio 2.06. Wages/economic sustainability, regions and
  international scope remain future work.
- Notebook 53: replaced the legacy `/v1/era5` request with `/v1/archive`, fixed
  `models=era5`, Celsius and Europe/Rome, retained the original 2002 start, and
  validated all 8,766 daily records through 2025. Raw six-year response chunks
  and query/hash/retrieval manifests are ignored under `data/sources/open_meteo/`.
  Downloads are spaced 31.1s after completion to account for weighted long-window
  provider quotas, with a 45s total deadline, 2 MiB cap and no retries. Each of
  the four actual requests returned HTTP 200 in under one second. No key was used.
- Corrected notebook 53's obsolete `-1` year shift: weather year y matches CCR
  column y (January y to January y+1). Zero-exposure years remain included.
  Signed Spearman correlations replace absolute values, with explicit sample
  sizes and 2020–2021 / 2003 exclusions. Destination age bands and migration/census
  limitations are explained. All-year heat/decline rho is 0.107 (n=24), 0.187
  excluding 2020–2021 (n=22), and 0.065 also excluding 2003 (n=21). The Milan ERA5
  proxy peaks in 2003 at 325.5 Celsius-days. These are exploratory associations,
  not heat-attributable death counts or causal results. New methods/results are
  in `data/heatwave_analysis_summary.json`; HTML, interactive figures and a PNG
  were regenerated, and the main presentation links to the updated notebook.
- Utilities are in `scripts/`; `requirements.txt` stays at the root by user
  preference. Raw `data/sources/`, HTTP `.cache/`, `.venv/` and bytecode are
  gitignored. Matching queries reuse same-Europe/Rome-day downloads during a
  live refresh; offline runs may use older sources. Diagnostic repeat protection
  now also expires at the calendar-day boundary. Plotly 5.24.1 in an isolated
  environment preserves the existing `<6` constraint.
- Retrieval: a quiet minute per live run; 30.1 seconds after response completion
  before another attempt; nonblocking shared lock; reviewed positional keys for
  seven bounded national queries (no implicit metadata downloads). A killable
  transport enforces 45s total, 5s connect/10s read timeouts, 8 MiB response size,
  eight attempts/eight minutes per run. Failures persist a shared halt. The
  explicit connectivity diagnostic uses 20s/64 KiB and one exact-URL/PID/expiry
  permit. JSONL events retain all request starts, completions and failures.
  See [the access audit](istat-access-audit.md) and
  [working instructions](copilot-instructions.md).
- Final validation: 29 offline safety/scientific tests and all 10 national-model checks pass;
  saved fertility, scenario totals and retirement outputs match recomputation.
  Checks cover source hashes/keys, sex totals, complete age/year grids, finite
  nonnegative populations, valid probabilities, retained observations, ordered
  official intervals and annual cohort accounting. Maximum rounding differences
  are 1.061 people per age/cohort transition and 0.962 births. The validation and
  retirement summaries are in `data/refresh_validation.json` and
  `data/retirement_summary.json`. Seven cached SDMX replies replayed identically
  with no metadata requests. No live API was used by automated tests.
- Presentation: exported PNGs were visually inspected and clipped analysis
  labels corrected. The attempted browser preview stalled and was interrupted;
  interactive browser QA remains uncompleted and was not retried. Local links,
  notebook/export consistency and whitespace were checked offline.
