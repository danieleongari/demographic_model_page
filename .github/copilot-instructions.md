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
  for the run. Respect `Retry-After`; do not probe repeatedly or evade a block
  through another IP. Report the failure and continue offline where possible.

## Repository map

- [`README.md`](../README.md): project context, source notes, and release history;
  some dataset descriptions are explicitly historical.
- [`notebooks/`](../notebooks/): source analyses, ordered by numeric prefix. Most
  local paths assume the working directory is `notebooks/`.
- [`notebooks/requirements.txt`](../notebooks/requirements.txt): declared Python
  dependencies and version constraints.
- [`data/`](../data/): checked-in inputs and derived model artifacts, including
  [`all_istat_dataflows.csv`](../data/all_istat_dataflows.csv) for offline discovery.
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
There is no configured automated test suite or build command in the repository.

The main artifact dependencies are:

| Notebook | Inputs / role | Outputs consumed downstream |
| --- | --- | --- |
| `00_get_dataset_filters` | ISTAT metadata exploration; use cached dataflow CSV first | Dataset and dimension discovery |
| `14_investigate_italian_residents` | Historical population retrieval | `pop_by_age_year.csv`, `cc_by_age_year.csv`, `ccr_by_age_year.csv` |
| `30_investigate_italian_deathprob` | Mortality retrieval | `deathprob_by_age_year.csv` |
| `40_investigate_italian_fertility` | Population and fertility observations | `fertility_fitted.json` |
| `45_investigate_italian_migration` | Population, cohort changes, and death probabilities | `average_migration_balance.csv` |
| `63_deathprob_projections` | Historical death probabilities | `deathprob_by_age_year_proj.csv` |
| `70_modelling_future_population` | Population, projected mortality, fertility fit, migration balance | `pop_by_age_year_proj.csv` and scenario figures |
| `73_analyse_future_population` | Historical and projected population | Population-analysis figures |
| `84_sustainable_retirement_age` | Historical and projected population, embedded historical retirement data | `sust_retirement_age.html` |

Notebook names in the table refer to `.ipynb` files under `notebooks/`; data
artifacts are under `data/`. Notebooks `20`, `25`, and `53` are supplementary
investigations, not prerequisites for every refresh. Numeric order alone is not
a reason to execute every notebook. Even notebook `70` includes an ISTAT request
for comparison data: inspect cells before assuming an analysis runs offline.

## Implement and validate changes

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
