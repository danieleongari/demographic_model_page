# Repository working instructions

These rules apply to the whole repository and all agents, including GitHub
Copilot sessions. Read this file before making changes, then read the
[current handoff](agent-handoff.md) for the latest status and limitations.
The root `AGENTS.md` is only a pointer to this file; keep all rules in `.github/`.

## Paramount rule: protect ISTAT access

**Never exceed 5 ISTAT API requests in any rolling 60 seconds per public IP.**
The [README data-source notes](../README.md#data-source) record that exceeding this
limit can block access for 1–2 days. Treat this as a hard constraint, including
during exploration, debugging, validation, and notebook execution.

- Prefer checked-in `data/`, saved outputs, and offline checks. Do not refresh
  ISTAT data just to verify an unrelated edit.
- Count every outgoing ISTAT request: data, dataflows, structures, codelists,
  automatic metadata fetches, pagination, redirects, and retries. Count failed
  requests too. One notebook cell or SDMX client call may send several requests.
- Serialize all ISTAT traffic through one shared limiter, allowing **at least
  15 seconds between actual outgoing requests**, including retries and implicit
  client requests. This margin does not replace the rolling-window limit.
- The budget is shared across notebooks, kernels, scripts, processes, agents,
  and other users on the same public IP. Never run ISTAT retrieval concurrently.
  If recent usage is unknown, establish an exclusive retrieval window and wait
  at least 60 seconds with no ISTAT traffic before starting. If shared usage
  cannot be coordinated, use cached data and report the limitation.
- Check all network paths before execution. Existing notebooks are **not** proof
  of safe throttling. Before adding or running live retrieval, ensure the limiter
  covers the underlying HTTP requests, disable uncontrolled retries, and cache
  responses. Do not use a whole-notebook or whole-repository run as a smoke test.
- On HTTP 429, a block response, or an access-denied response, stop ISTAT calls
  for the current retrieval attempt. Respect `Retry-After`; do not probe
  repeatedly or change IP/endpoints automatically. Report the failure, follow
  the user-directed VPN recovery procedure below, and continue offline where
  possible.
- Distinguish a locally persisted safety halt from a confirmed provider IP block.
  A local halt does not establish that ISTAT blocked the public IP, and changing
  networks/VPN does not clear that local state. Explain the distinction before
  recommending connectivity troubleshooting; do not infer a remote block from a
  hanging UI or a timeout alone.
  Be technically precise: a VPN can change the public source IP and could bypass
  a restriction based solely on the old IP. This possibility does not clear the
  local halt, establish the cause of a stall, or authorize automatic IP rotation.
  Another computer on the same ordinary home connection usually shares
  the public IP.
- Treat a hang/timeout, interrupted retrieval, transport/HTTP error, unexpected
  SDMX reply, or oversized response as a possible service/block condition too:
  stop **all** live retrieval, preserve the shared halted state, and do not retry,
  change endpoint/IP, or clear the halt automatically. Cached analysis may
  continue. A slow response is not permission to raise the timeout.
- **User-directed VPN recovery (standing user preference, 2026-11-11):** When
  an actual ISTAT API request is blocked or hangs, stop traffic and **ask the
  user to turn on their VPN** (their current setup is Surfshark, Italy). If it is
  already enabled, report that and ask them to check/reconnect it. Explain the
  observed error; do not assume every timeout proves an IP block. Do not trigger
  this prompt solely because a local halt flag exists.
  The prompt should explain that confirmation will authorize **one tiny guarded
  connection check**, so a second confirmation is unnecessary when the user says
  they are ready. Wait for that confirmation, respect any explicit `Retry-After`,
  establish a quiet minute, then use the single-request diagnostic below.
  Never enable/switch the VPN or rotate exit servers automatically. If the
  check fails, stop and report; do not loop through servers or endpoints. After
  a successful check and user-authorized continuation, review any local halt
  under the shared lock before resuming only the live work actually needed.
  Preserve audit history, request counters, deadlines and caching. Prefer the
  existing sources when they already satisfy the task. This user preference
  supersedes the earlier blanket guidance against requesting a VPN change.

## Repository map

- [`README.md`](../README.md): project context, source notes, and release history;
  some dataset descriptions are explicitly historical.
- [`scripts/`](../scripts/): retrieval, refresh runner, offline validation and safety tests.
- [`notebooks/`](../notebooks/): notebook analyses only, ordered by numeric prefix. Most
  local paths assume the working directory is `notebooks/`.
- [`requirements.txt`](../requirements.txt): declared Python
  dependencies and version constraints.
- [`data/`](../data/): checked-in inputs and derived model artifacts, including
  [`all_istat_dataflows.csv`](../data/all_istat_dataflows.csv) for offline discovery.
- `data/sources/` (gitignored): local raw tidy source snapshots and JSON manifests
  (dataset IDs, filters, coverage, retrieval timestamps, request URLs and hashes).
  Never commit these downloads. Reuse a matching query only within the same
  calendar day in Europe/Rome when refreshing; an explicit offline run may use
  older saved sources. A fresh checkout needs one authorized live refresh.
- [`scripts/istat_source.py`](../scripts/istat_source.py): the maintained
  retrieval entry point. Its HTTP session covers implicit SDMX metadata calls,
  uses a nonblocking shared file lock, waits 60 seconds per live run, and waits
  at least 30.1 seconds after completion before another attempt. This permits at
  most two requests per rolling minute. Retries and redirects are disabled.
  A subprocess transport enforces a 45-second total deadline (including DNS,
  TLS and a slow response body), with 5s connect/10s read timeouts and an 8 MiB
  body limit. The subprocess also has its own termination alarm. A run has at
  most eight attempts and eight minutes; failures freeze live retrieval across
  sessions. Start/finish events are retained in a JSONL audit log alongside the
  shared limiter. Do not infer request start times from cache file mtimes.
  The temporary limiter is shared across checkouts for this OS account; it cannot
  coordinate other users or devices on the same public IP. Coordinate those
  separately. Do not clear a blocked limiter and retry automatically; follow the
  user-directed VPN recovery and authorization procedure above.
  A precautionary halt was placed on 2026-11-11 after the user's report of a long
  stall. After a successful authorized VPN check and explicit user continuation,
  that precautionary halt was reviewed and cleared under the lock; counters and
  audit history were retained. No additional API calls were needed. Review any
  future halt and user authorization before resuming; do not send unrequested
  probes.
  On explicit new user authorization, `scripts/check_istat_connection.py --live`
  permits one fixed national TFR observation using an expiring, process- and
  exact-URL-scoped ticket. This consumes the ticket while keeping the general
  halt set. It waits a quiet minute, sends no metadata requests/retries, and caps
  the request at 20 seconds and 64 KiB. Without `--live` it is a dry run; an
  existing same-day diagnostic cache prevents repeating the same probe. Do not run this
  command without a fresh user request, or retry it after failure. A tiny
  successful response does not establish that a VPN caused recovery or that a
  larger query will work. The 2026-11-11 user-authorized VPN check succeeded with
  exactly one request. All ordinary retrieval limits and failure stops remain
  in force after the user's subsequent continuation request.
  Compressed HTTP responses in ignored `.cache/istat/` are reused on the same day.
- [`index.html`](../index.html): static presentation; embeds figures from
  [`images_output/`](../images_output/) and links to [`notebooks_html/`](../notebooks_html/).
- [`images_other/`](../images_other/): supporting static assets.

## Main work and planned extensions

Maintain and update the existing Italy model and presentation. The current model
projects population under nine fertility/migration scenarios; notebook `84` uses
a working-age/retirement-age population ratio as its retirement-age proxy.

Future directions requested by the maintainer (not yet implemented):

1. Include wages and economic assumptions in the retirement sustainability
   estimate, beyond population ratios alone.
2. Apply the analysis to cities such as Milan and to Italian regions.
3. Extend the model and comparisons to an international context.

Use the extension guidance below; preserve a reproducible national demographic
baseline when adding these capabilities.

## Required maintenance after every intervention

Before finishing **every intervention**, update the relevant guidance in
`.github/` to reflect changes to paths, workflow rules, model scope, and
implementation status, then replace the [current handoff](agent-handoff.md).
Even if no lasting rule changed, record what was done, what was checked, and any
remaining limitation. For a read-only investigation, record the findings without
implying code changed. Keep `AGENTS.md` as a short redirect; it does not need a
routine handoff edit. Update the README when public behavior, sources, or
conclusions change. Do not mark planned work complete until it is implemented
and validated.

## Start with the relevant source

Inspect the working tree and preserve unrelated edits. Read the README and the
affected notebook's Markdown, code, and saved outputs before changing assumptions.
Use notebook sources rather than editing exported HTML as the primary analysis.
Focused offline tests and refresh/export commands are documented below; no
external CI pipeline is configured.

The main artifact dependencies are:

| Notebook | Inputs / role | Outputs consumed downstream |
| --- | --- | --- |
| `00_get_dataset_filters` | ISTAT metadata exploration; use cached dataflow CSV first | Dataset and dimension discovery |
| `14_investigate_italian_residents` | Historical population retrieval | `pop_by_age_year.csv`, `cc_by_age_year.csv`, `ccr_by_age_year.csv` |
| `30_investigate_italian_deathprob` | Mortality retrieval | `deathprob_by_age_year.csv` |
| `40_investigate_italian_fertility` | Population and fertility observations | `fertility_fitted.json` |
| `45_investigate_italian_migration` | Population, cohort changes, and death probabilities | `average_migration_balance.csv` |
| `53_correlate_deaths_heatwaves_2003` | Cached cohort changes and Open-Meteo ERA5 near Milan | `heatwave_analysis_summary.json`, exploratory heat/cohort figures; optional |
| `63_deathprob_projections` | Historical death probabilities | `deathprob_by_age_year_proj.csv` |
| `70_modelling_future_population` | Population, projected mortality, fertility fit, migration balance | `pop_by_age_year_proj.csv` and scenario figures |
| `73_analyse_future_population` | Historical and projected population | Population-analysis figures |
| `84_sustainable_retirement_age` | Historical and projected population, embedded historical retirement data | `sust_retirement_age.html`, `retirement_age_by_year.csv` |
| `86_retiree_life_expectation` | Annual retirement ages from `84`, observed mortality from `30`, projected mortality from `63` | Remaining-life CSVs, method/provenance JSON, interactive HTML and static PNG |

Notebook names in the table refer to `.ipynb` files under `notebooks/`; data
artifacts are under `data/`. Notebooks `20`, `25`, and `53` are supplementary
investigations, not prerequisites for every refresh. Numeric order alone is not
a reason to execute every notebook. Even notebook `70` includes an ISTAT request
for comparison data: inspect cells before assuming an analysis runs offline.

### Maintained refresh workflow

Use the existing Python environment with the dependencies in
`requirements.txt` (including a Jupyter Python kernel and `nbmirror`).
From the repository root:

```sh
python scripts/refresh_model.py --refresh  # explicit, serialized live retrieval
python scripts/refresh_model.py            # saved sources only; HTTP disabled
python -m unittest discover -s scripts -p 'test_*.py'  # mocked retrieval checks
```

The runner reads notebook `00`'s cached catalogue, then executes `14`, `30`, `40`,
`45`, `63`, `70`, `73`, `84`, `86` in order and exports each with `nbmirror`. In `00`
only the catalogue cells are executed: the rest remains optional exploration.
`--download-only --refresh` separates retrieval from execution;
`--from-notebook 40` (or another maintained prefix) resumes offline execution.
The final validator writes tracked `data/refresh_validation.json`, including source
coverage, accounting checks, and differences from `HEAD`'s checked-in model.
The baseline comparison therefore means the current Git `HEAD`, not a fixed
historical release. Main notebooks use `istat_data()` and never refresh on an
ordinary run. The World Bank comparison is also cached. Supplementary notebooks
`20`, `25`, `53` are outside this runner. `20`/`25` install the shared guard before
legacy imports: plain `requests`/`istatapi` ISTAT traffic is rejected. Their old
saved outputs remain historical. Notebook `53` has a separate optional runner:

```sh
python scripts/refresh_model.py --heatwaves --refresh  # Open-Meteo only
python scripts/refresh_model.py --heatwaves            # offline notebook 53
```

The weather branch never calls ISTAT and does not rerun the national model.
`scripts/weather_source.py` downloads daily ERA5 minimum/maximum temperatures near
Milan through `/v1/archive`, explicitly fixing `models=era5`, Celsius and
`Europe/Rome`. No API key is needed for the public noncommercial service. Raw
JSON and source manifests stay in ignored `data/sources/open_meteo/` (a subfolder
separate from the national source manifests). Matching same-day queries reuse
downloads. Six-year chunks are separated by 31.1s after completion because long
date windows count as multiple Open-Meteo calls. The locked, killable transport
has a 45s total deadline, no retries/redirects and a 2 MiB response limit. Weather
failures stop its own retrieval without changing the ISTAT limiter.

The heatwave comparison preserves the 2002 start and ends at the latest complete
common weather/cohort year (currently 2025). Require complete daily coverage,
Celsius units, no duplicate dates, finite temperatures and Tmin ≤ Tmax. Keep
zero-exposure years. Match weather year `y` directly to CCR column `y`, the
transition from January `y` to January `y+1`; do not reintroduce the old `-1`
year shift. The age bands refer to destination ages in the next January.
`scripts/heatwave_analysis.py` reports signed Spearman correlations with sample
sizes and exclusions for 2020–2021 and, separately, 2003. Do not take absolute
values or interpret cohort change as actual deaths. A single Milan reanalysis
point, secular trends, migration and census revisions limit causal claims.
`heatwave_analysis_summary.json` contains derived statistics and provenance;
daily weather downloads are never committed. The notebook saves interactive
heat/cohort and age-sensitivity figures plus a standalone PNG and HTML export.

The seven maintained national data queries use reviewed positional dimension
keys, so SDMX does not implicitly retrieve full dataflow structures/codelists.
Unknown flows/dimensions or unrestricted geography require deliberate migration
before retrieval. The helper blocks unguarded ISTAT `requests` clients too.

The 2026-11 refresh uses final full-year 2025 fertility observations, residents
on 1 January 2026, and ISTAT base-2025 official projections through 2080. Keep the
provisional January–July 2026 fertility estimate separate. The model's effective
fertility coefficient reproduces next-January age-0 residents under its 50%
women assumption; it is not the official total fertility rate. Calibration and
forecasting use the same fitted age distribution (18–50). Migration residuals
use origin-age mortality and only complete overlapping observation years.
Mortality projections use the latest 12 available non-COVID observation years
for their recent-average component. The original nine scenario definitions,
100+ mortality assumption and demographic retirement-ratio scope are retained.
Pre-2019 population is retained from the full Plotly figure in the Git `HEAD`
population notebook and checked against the population matrix, rather than
queried again from slow historical endpoints. Its local cache manifest identifies
the source Git commit and explicitly labels it as retained data. Keep
`plotly_mimetype+notebook` output in the maintained notebooks so this saved series
remains recoverable on fresh checkouts. `retirement_summary.json` records the
current reference ratio and scenario range for the 1990 birth cohort.

Notebook `84` also exports calendar-year retirement ages to
`retirement_age_by_year.csv`: one historical/current row per population year,
tagged as an observed effective age or an assumption, and nine scenario rows
per future year. Keep its existing ratio search and scenario labels unchanged
when exporting. Notebook `86_retiree_life_expectation` consumes this file plus
the checked-in mortality CSVs and needs no raw snapshots or live access.
`python scripts/refresh_model.py --from-notebook 84` regenerates both analyses;
`--from-notebook 86` reuses the existing annual retirement-age export.

The `86` measure is **period remaining life expectancy conditional on reaching
the retirement age in that calendar year**, not cohort expectancy or life
expectancy at birth minus retirement age. Reuse `63`'s mortality probabilities,
shared across all nine fertility/migration scenarios; do not fit an independent
longevity trend or force a smooth observed/projected boundary. Use the full
single-age ISTAT series through 119, uniform within-age deaths, conditional
fractional ages, and an analytic tail repeating q119. This detailed life-table
calculation intentionally differs from `70`'s 40% mortality assumption in its
aggregate 100+ population bin. The tail sensitivity is recorded in the summary.
Historical effective retirement ages are the unweighted male/female mean from
`84`, available through 2023; 2024–2026 use its assumed age 64. Mortality is
observed through 2025, projected from 2026, and scenario retirement ages begin
in 2027. Preserve these observation/assumption/projection distinctions in all
exports. Keep notebook 86's interactive chart consistent with the adjacent
retirement-age chart: standard `plotly` background, no title or legend, no
projection-background shading, and a 780×320 figure in a 350px main-page iframe.
Retain scenario names in hover and the existing scenario colors. Its Matplotlib
companion keeps its independent title, legend and layout; presentation-only
interactive changes should not regenerate that PNG or numerical exports.
Derived outputs are `retiree_life_expectancy_by_year.csv`,
`retiree_fixed_age_life_expectancy.csv`, `retiree_life_expectancy_summary.json`,
and `images_output/retiree_life_expectancy.{html,png}`. Pure transformations and
analytical tests live in `scripts/retiree_life_expectancy.py` and
`scripts/test_retiree_life_expectancy.py`; the national validator checks annual
scenario coverage, alignment with the 1990 cohort, expectancy values and hashes.
Record retrieval time from a matching local mortality source manifest when
available; otherwise leave it null and retain input hashes, rather than inventing
a new retrieval date. The November 2026 baseline came from 11 November's cache.

## Implement and validate changes

- **Standing language preference:** For every reader-facing ISTAT link in the
  main page, README, notebook sources and their HTML exports, use the official
  English page when it exists and can be found. Keep the original Italian page
  or document only when no English equivalent exists or can be found. Verify the
  actual destination and matching subject/reference period; do not invent URLs
  by translating slugs or point to an older release to obtain English text.
  English translations may have different publication dates or misleading year
  headings: preserve the data reference year and distinguish the original release
  date from the English page's date. Regenerate affected notebook mirrors without
  executing analyses for link-only edits. This preference does not change API
  endpoints, cached provenance or the ISTAT retrieval safety rules.
- Keep notebook edits focused; preserve cell identities and avoid unrelated
  output churn. Preserve the Plotly version constraint in the requirements.
  Check actual imports when preparing an environment; the declared dependencies
  do not cover every exploratory notebook.
- Preserve age/year indexing, units, sex categories, scenario labels, and CSV
  schemas unless deliberately migrating their consumers. Document source IDs,
  filters, observation years, retrieval dates, transformations, and assumptions
  for new or refreshed data. Distinguish observations from projections.
- For model changes, check relevant invariants offline: nonnegative populations,
  probabilities within valid bounds, complete age/year coverage, no duplicate
  keys, consistent totals, and cohort accounting for births, deaths, and migration.
  Compare changed results against the checked-in baseline and explain differences.
- Validate only the affected dependency chain. Use cached inputs, synthetic data,
  or mocked responses for tests; never contact ISTAT from an automated test.
  Any live refresh must obey the ISTAT rules above.
- Regenerate affected figures and notebook HTML when publishing changed analysis.
  The README identifies `nbmirror` as the notebook exporter; inspect the available
  tooling before choosing a command. Keep `index.html` links, embedded figures,
  explanatory text, and README conclusions consistent with the new results.
  Inspect changed presentation assets visually and check their local links.
- Maintain the `index.html` `.data-update` source box when revising the main-page
  summary or publishing refreshed model inputs. Use an explicit ISO page-update
  date in `<time datetime="YYYY-MM-DD">`, followed by three bullets: population
  observation date, final official fertility rate and reference year, and ISTAT
  projection base date and horizon. Link each bullet to its official release,
  labelled `ISTAT YYYY-MM-DD` with the verified publication date. Cross-check
  coverage and fertility against the checked-in data; keep provisional estimates
  separate in the README source notes. An unchanged offline rerun does not advance
  the page-update date. Do not restore a `document.lastModified` footer timestamp.
- Finish by updating `agent-handoff.md` and any affected `.github/` guidance, inspecting
  the diff, and reporting changes, validation, and unresolved limitations. State
  when results or exports could not be regenerated rather than implying success.

## Extend the model deliberately

**Wages and economic sustainability.** Start from notebook `84`; retain its
demographic ratio as an explicit baseline. Working-age residents are not the
same as employed contributors. Define a separate economic balance using relevant
employment/participation, wage or earnings profiles, contribution rates, and
pension outlays or benefit assumptions. State real/nominal units, price year,
coverage, and productivity/wage-growth assumptions. Do not infer fiscal
sustainability from wages alone; test sensitivity to the added assumptions.

**Cities and regions.** Make geography and dataset filters explicit instead of
overwriting the Italy artifacts. Distinguish Milan municipality, metropolitan
city, and region. Verify age/sex detail, consistent geographic codes and boundary
changes, internal versus international migration, and small-population effects.
Document that a local demographic or wage balance is not a separate local pension
system. Reconcile regional totals with national figures where coverage permits.

**International scope.** Separate source retrieval and country-specific parameters
from reusable projection logic as needed. Check comparability of age bands,
reference dates, population coverage, mortality, fertility, migration, employment,
and pension definitions. Document currency, inflation, and purchasing-power
treatment for wage comparisons. Choose authoritative sources appropriate to each
country, respect each provider's limits, and validate against Italy's baseline
before presenting cross-country conclusions.

Treat these as future work until implemented. Prefer a small, reproducible
extension with explicit assumptions over silently changing the existing model.
