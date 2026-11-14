# Demographic Model Page

🌐 View the presentation at https://danieleongari.github.io/demographic_model_page/

🔗 Original project from deprecated https://github.com/danieleongari/saturdaymorningdsprojects.

Agent contributors: [AGENTS.md](AGENTS.md) points to the
[repository working instructions](.github/copilot-instructions.md) in `.github/`.

🗣️ Posted on:

- [Linkedin (Italian)](https://www.linkedin.com/posts/danieleongari_i-was-born-in-1990-and-i-will-retire-in-italy-activity-7051629734937411584-eDWZ) - 2023, April
- [Linkedin (Italian)](https://www.linkedin.com/posts/danieleongari_ho-preso-gli-ultimi-aggiornamenti-istat-e-activity-7181748786174586881-F5hI) - 2024, April
- [Reddit r/ItaliaPersonalFinance](https://www.reddit.com/r/ItaliaPersonalFinance/comments/1bwcg3g/ho_preso_gli_ultimi_aggiornamenti_demografici/) - 2024, April
- [Reddit r/dataisbeautiful](https://www.reddit.com/r/dataisbeautiful/comments/1jmkoul/demographic_model_of_italy_what_the_future_could/) - 2025, March
- [Linkedin (Italian)](https://www.linkedin.com/posts/danieleongari_con-i-dati-pubblicati-da-istat-questa-mattina-activity-7312426628574330880-wiUa) - 2025, March
- [YouTube EconomiaItalia (Italian)](https://youtu.be/y7qPip1zdAU) - 2025, April

## Notebooks

- Exploring data
  - `investigate_italian_residents` - explore datasets for registered residents in Italy: `DCIS_RICPOPRES2011` and `DCIS_POPRES1`
  - `investigate_italian_deaths` - compare datasets `DCIS_MORTALITA1` and `DCIS_DECESSI` to spot the differences
  - `compare_deaths_deltaresidents` - compare deaths with the change in residents to spot the migration balance
  - `investigate_italian_deathprob` - spot trents in mortality over the years of observation, since 1974
  - `investigate_italian_fertility` - explore dataset `DCIS_FECONDITA1` and reconcile data with the population dataset 
  - `investigate_italian_migrations` - explore dataset `DCIS_MIGRAZIONI` and reconcile data with the population dataset
- Analyzing data
  - `53_correlate_deaths_heatwaves_2003` - explore Milan heat exposure and Italy's cohort changes, with corrected calendar alignment and sensitivity checks
- Making predictions
  - `projection_death_prob` - predict the future mortality rate based on past data 
  - `modelling_future_population` - predict future population based on past data and several extreme assumptions (scenarios)
  - `analyze_future_population` - opinionated plots on how the future population will look like, based on the previous notebook
  - `sustainable_retirement_age` - compute, for each generation, the retirement age to keep a consistent ratio of workers/retired
  - `86_retiree_life_expectation` - plot remaining period life expectancy at each calendar year's retirement age, using observed ISTAT age-specific mortality and all nine future retirement-age paths

## Reproducing the model

Python dependencies are in [`requirements.txt`](requirements.txt). Install them in
an isolated environment with a Python Jupyter kernel. The Plotly `<6` constraint
is intentional. All non-notebook utilities are in [`scripts/`](scripts/).

```sh
python -m pip install -r requirements.txt
python scripts/refresh_model.py --refresh
```

Live retrieval is serialized through a shared limiter: a quiet minute per live
run, at least **30.1 seconds after each completed request** before another starts
(at most two requests per rolling minute), and no retries or redirects. Every
request has a **45-second total deadline**, 5-second connection and 10-second
read timeouts, and an 8 MiB response limit. The network worker is killed at the
deadline, including during a slow/dripping response. A refresh is limited to
eight live attempts and eight minutes. Any timeout, interruption, HTTP error,
unexpected SDMX response, or size/budget violation halts subsequent live access
across sessions until explicitly reviewed. A busy limiter fails immediately
instead of queuing. Coordinate other ISTAT
usage on the same public IP before starting. Matching query parameters reuse
downloads from the same calendar day in Europe/Rome. Raw source CSVs and their
manifests stay in **gitignored `data/sources/`**; HTTP responses and the local
environment are ignored too. A fresh checkout therefore needs a live refresh.

The pre-2019 population baseline is retained from the existing notebook's full
saved figure and checked against the existing population CSV. It is not presented
as freshly downloaded historical data. Current population since 2019 and the
other maintained sources are refreshed from ISTAT. To recompute from local
sources with HTTP disabled:

```sh
python scripts/refresh_model.py
python -m unittest discover -s scripts -p 'test_*.py'
```

The runner checks notebook `00`'s cached catalogue, then executes `14`, `30`, `40`,
`45`, `63`, `70`, `73`, `84`, and `86` in dependency order, exports notebook HTML with
`nbmirror`, and records offline checks and changes from the Git `HEAD` model in
[`data/refresh_validation.json`](data/refresh_validation.json). Optional
investigations `20`, `25` and the live exploration cells of `00` are outside
this runner; notebook `53` uses the separate option below. `--refresh --download-only` saves sources only;
`--from-notebook 40` resumes offline execution at a maintained notebook.
The seven maintained national queries use explicit SDMX dimension order, avoiding
automatic metadata/codelist requests. New dataflows and unbounded geographical
queries are rejected. Start/finish times, URLs, durations and failures are logged
beside the shared temporary limiter. See the
[request-safety audit](.github/istat-access-audit.md). Legacy ISTAT retrieval in
notebooks `20` and `25` is disabled until migrated to the guarded client.
If ISTAT blocks or stalls, the agent stops and asks the user to enable their VPN
(or check it if already enabled). After confirmation, one small connection check
uses the same request limiter and strict deadlines. VPN switching and repeated
probes are never automatic; cached work continues where possible.

To rebuild the retirement analysis from the checked-in population and mortality
CSVs, without refreshing any source:

```sh
python scripts/refresh_model.py --from-notebook 84
```

Notebook `84` exports [`data/retirement_age_by_year.csv`](data/retirement_age_by_year.csv),
and [`86_retiree_life_expectation.ipynb`](notebooks/86_retiree_life_expectation.ipynb)
uses each year's death probabilities to calculate remaining life conditional on
reaching that year's retirement age. Historical mortality comes from notebook
`30`; future mortality reuses notebook `63`, shared across the nine scenarios.
The measure is **period** life expectancy, holding the selected year's mortality
schedule fixed over the remaining lifetime. It uses all single ages through 119,
uniform deaths within each age interval, conditional fractional retirement ages,
and an analytic tail repeating the age-119 probability. The 2024–2026 retirement
age of 64 is an explicit assumption inherited from `84`; effective-age
observations end in 2023. Mortality observations end in 2025.

The [interactive chart](images_output/retiree_life_expectancy.html),
[static figure](images_output/retiree_life_expectancy.png),
[annual results](data/retiree_life_expectancy_by_year.csv), and
[method/provenance summary](data/retiree_life_expectancy_summary.json) are exported
offline. In 2100, the nine scenarios give retirement ages of 66–78 and remaining
life expectancies of 13.1–23.1 years. At a fixed age of 65, remaining life rises
from 21.4 years in 2025 to 24.0 in 2100 under the existing mortality projection.

Notebook `53` can be refreshed separately:

```sh
python scripts/refresh_model.py --heatwaves --refresh
python scripts/refresh_model.py --heatwaves  # cached weather; HTTP disabled
```

This fetches only [Open-Meteo historical weather](https://open-meteo.com/en/docs/historical-weather-api),
with no ISTAT requests and no API key for noncommercial use. ERA5 is selected
explicitly to keep the model consistent across years. Complete 2002–2025 daily
temperatures near Milan are cached in gitignored `data/sources/open_meteo/`, with
query parameters and retrieval dates. Six-year chunks, spaced 31.1 seconds after
completion, avoid a single large request and account for the provider's weighted
call limits. Each request has a 45-second total deadline and no retries.

The analysis now matches weather year `y` to the cohort transition from January
`y` to January `y+1`, retains zero-exposure years, and reports signed correlations
and sensitivity to pandemic years and 2003. Cohort decline includes migration
and statistical revisions and is not a mortality rate. Derived results are in
[`data/heatwave_analysis_summary.json`](data/heatwave_analysis_summary.json).
Weather attribution: ERA5 / ECMWF / Copernicus C3S via Open-Meteo, CC BY 4.0;
monthly means and annual heat exposure are calculated in this project.

## ChangeLog

- 2026 November
  - Add notebook `86_retiree_life_expectation`, conditional remaining life at
    retirement for 1974–2100, all nine projected retirement-age paths, offline
    exports, and analytical life-table checks.
  - Refresh the national model using [final 2025 fertility data, released on 21 October 2026](https://www.istat.it/comunicato-stampa/natalita-e-fecondita-della-popolazione-residente-anno-2025/),
    and [ISTAT population and fertility projections based on 1 January 2025](https://www.istat.it/comunicato-stampa/previsioni-della-popolazione-residente-delle-famiglie-e-delle-forze-di-lavoro-base-1-1-2025/).
  - Keep the provisional January–July 2026 fertility estimate separate from full-year observations.
  - Use the same fitted fertility-age parameters for calibration and projection;
    align migration residuals with origin-age mortality; roll the mortality
    recent-average window forward to the latest available observations.
  - Add opt-in, rate-limited source retrieval, local same-day caching, ordered
    offline execution, and demographic accounting validation.

- 2026 May
  - Update with 2025 data ([press release](https://www.istat.it/en/press-release/indicatori-demografici-anno-2025/)) 
  - Finalize replacement of `istatapi` with `sdmx` for ISTAT data retrieval
  - For the population, use `RICPOPRES` data back to 1952
  - Include gender split in some graphs 
  - Include [better data](https://github.com/danieleongari/demographic_model_page/issues/3) for historical retirement age and plot it with future projections

- 2026 March
  - Using different APIs: `sdmx` for ISTAT and `wbgapi` for World Bank
  - Update fertility stats with [2024 data released last October](https://www.istat.it/en/press-release/births-and-fertility-of-the-resident-population-year-2024/).
  - Deprecate [nbviewer](https://nbviewer.jupyter.org/github/danieleongari/demographic_model_page/tree/main/notebooks/) in favour of local htmls created with [nbmirror](https://github.com/danieleongari/nbmirror)
  
- 2025 March
  - Revamp the population projections on 3x3 scenarios 
  - add more plots about the future population
  - Revamp the website 
  - Update with 2024 data ([press release](https://www.istat.it/comunicato-stampa/indicatori-demografici-anno-2024/)) but note that this is still a partial update because it still lacks the latest mortality and fertility data

- 2025 January
  - More in depth analysis for mortality, fertility rates, and migration balance: comparing my calculations from the 
    change in population, with the official ISTAT data for these observables

- 2024 June
  - Moved the whole analysis to this repository (`DEPRECATION` label on [StaurdayMorningDSProjects](https://github.com/danieleongari/saturdaymorningdsprojects) repo)
  - Try to consider mortality data

- 2024 April
  - Updated with 2024 data
  - Better but still approximate estimation of mortality/migration split
  - Conceived 9 scenarios for future mortality and migration balance
  - Created Pages visualization

- 2023 April
  - First release of the project on https://github.com/danieleongari/saturdaymorningdsprojects
  - In hindsight, my retirement age of 76 was overestimated due to the rough extrapolation of future population change, without splitting into mortality and migration balance

## Data Source

In 2026 the best way to retrieve ISTAT data is [sdmx](https://www.istat.it/en/classifications-and-tools/sdmx-web-services/).

> NOTE: To prevent SDMX web service overloading, a limit of 5 queries per minute has been set for each IP. Once this limit is exceeded, an access block lasting between 1 and 2 days is activated.

The maintained national sources use these SDMX dataflows. Query filters and
retrieval timestamps are recorded locally with each cached response; a compact
provenance summary accompanies the tracked validation report.

| Input | SDMX dataflow | Current coverage / interpretation |
| --- | --- | --- |
| Population | `22_289_DF_DCIS_POPRES1_1` | Residents on 1 January, since 2019; earlier years retained from the existing reconstruction baseline |
| Death probability | `26_295_DF_DCIS_MORTALITA1_2` | Annual single-age probabilities; source values per thousand converted to probabilities |
| Official fertility | `25_326_DF_DCIS_FECONDITA1_5` | Full-year TFR by mother's citizenship |
| Fertility age profile | `25_326_DF_DCIS_FECONDITA1_7` | Age-specific rates per thousand women |
| Migration comparison | `28_185` | Immigration/emigration with abroad, by age group and citizenship |
| Population projections | `165_889_DF_DCIS_PREVDEM1_1` | Base 1 January 2025, through 2080 |
| Fertility projections | `165_889_DF_DCIS_PREVDEM1_3` | TFR assumptions, base 2025, through 2080 |

The official full-year 2025 TFR is **1.14**. The model separately calibrates an
effective rate to reproduce age-0 residents on the following 1 January under its
50% women and fitted age-profile assumptions. These quantities differ and should
not be labelled interchangeably. The nine model scenarios are sensitivity
assumptions; ISTAT's central 80% uncertainty interval is a separate comparison.
The retirement calculation remains a population-ratio proxy, without wages,
employment or pension-finance modelling.

### Historical source notes

The legacy IDs and coverage below describe earlier versions of this analysis.
For discovery, use the saved catalogue first, or browse
[IstatData](https://esploradati.istat.it/databrowser/#/en/dw/categories).

### `DCIS_POPRES1` - Resident population on 1st January
- yearly (2019-latest) population by age, gender, town, marital status (no citizenship)

### `DCIS_POPORESBIL1` - Resident population  - balance
- mirror of `DCIS_POPRES1` (2019-latest) but with aggregated data (i.e., no split by age and marital status)
- many more information (some yearly other monthly), e.g., residents, births, deaths.
- I found this [unavailable on 2024-06-29](https://github.com/Attol8/istatapi/issues/27)
- PROBLEM: I need the age split for my models

### `DCIS_RICPOPRES2011` - Estimated resident population - Years 2002-2019
- yearly, 2002-2018, population by age, gender, town, citizenship (no marital status)
- data is reconstructed as explained [here](https://demo.istat.it/data/ricostruzione/Ricostruzione-popolazione_2002_2018.pdf)
- has data such ad population, live births, deaths
- PROBLEM: no consistent data for 2019-later available

### `DCIS_RICSTAT` - New series of estimates on the resident population at NUTS-2 level for the 1/1/2002-1/1/2014 period
- only available to OECD iLibrary subscribers.

### `DCIS_PREVDEM1` - Demographic projections - Years 2018-2065
- demographic projections from latest to 2080, with lots of predicted stats, by region and age
- confidence intervals are also provided
- useful to compare with my models and scenarios

### `DCIS_POPSTRBIL1` - resident foreigners 
- equivalent to `DCIS_POPORESBIL1` with aggregated data (i.e., not split by age) about foreigners
- nothing useful for my purposes here, so far

### `DCIS_FECONDITA1`: yearly (1999-2021) fertility rate and related info
- 1999-latest, yearly
- by citizenship (`ITL`/`FRG`), mother's age, province
- `TIPO_DATO`: age-specific fertility rate, father's average age, mohter's average age, total fertility rate

### `DCIS_DECESSI` - Deaths
- 2011-latest, yearly
- residents canceled from Anagrafe (`TIPO_DATO=='DEATH'`) and derived statistics 
- divided by country of citizenship, country of birth, marital status, province
- PROBLEM: not by age, only age groups 0-4, 5-9, 10-14, etc.

### `DCIS_MORTALITA1` - Life tables
- 1974-latest, yearly
- contains the `FUNZ_BIO=='DEATHS'` by age, but this is a number that sum up to 100'000 for all ages: this is some kind of "pseudostationary" population from which you can not extract the real number of deaths as in `DCIS_DECESSI`
