# Demographic Model Page

🌐 https://danieleongari.github.io/demographic_model_page/

🔗 Original project from deprecated https://github.com/danieleongari/saturdaymorningdsprojects.

🗣️ Posted on:

- [Linkedin (Italian)](https://www.linkedin.com/posts/danieleongari_i-was-born-in-1990-and-i-will-retire-in-italy-activity-7051629734937411584-eDWZ) - 2023, April
- [Linkedin (Italian)](https://www.linkedin.com/posts/danieleongari_ho-preso-gli-ultimi-aggiornamenti-istat-e-activity-7181748786174586881-F5hI) - 2024, April
- [Reddit r/ItaliaPersonalFinance](https://www.reddit.com/r/ItaliaPersonalFinance/comments/1bwcg3g/ho_preso_gli_ultimi_aggiornamenti_demografici/) - 2024, April
- [Reddit r/dataisbeautiful](https://www.reddit.com/r/dataisbeautiful/comments/1jmkoul/demographic_model_of_italy_what_the_future_could/) - 2025, March
- [Linkedin (Italian)](https://www.linkedin.com/posts/danieleongari_con-i-dati-pubblicati-da-istat-questa-mattina-activity-7312426628574330880-wiUa) - 2025, March
- [YouTube EconomiaItalia (Italian)](https://youtu.be/y7qPip1zdAU) - 2025, April

## Notebooks

📈 Visualize the notebooks with interactive plotly graphs on [nbviewer](https://nbviewer.jupyter.org/github/danieleongari/demographic_model_page/tree/main/notebooks/).

- Exploring data
  - `investigate_italian_residents` - explore datasets for registered residents in Italy: `DCIS_RICPOPRES2011` and `DCIS_POPRES1`
  - `investigate_italian_deaths` - compare datasets `DCIS_MORTALITA1` and `DCIS_DECESSI` to spot the differences
  - `compare_deaths_deltaresidents` - compare deaths with the change in residents to spot the migration balance
  - `investigate_italian_deathprob` - spot trents in mortality over the years of observation, since 1974
  - `investigate_italian_fertility` - explore dataset `DCIS_FECONDITA1` and reconcile data with the population dataset 
  - `investigate_italian_migrations` - explore dataset `DCIS_MIGRAZIONI` and reconcile data with the population dataset
- Analyzing data
  - `correlate_deaths_heathwaves_2003` - correlate deaths with heatwaves to spot the bump in mortality in 2003
- Making predictions
  - `projection_death_prob` - predict the future mortality rate based on past data 
  - `modelling_future_population` - predict future population based on past data and several extreme assumptions (scenarios)
  - `analyze_future_population` - opinionated plots on how the future population will look like, based on the previous notebook
  - `sustainable_retirement_age` - compute, for each generation, the retirement age to keep a consistent ratio of workers/retired

## ChengeLog

- 2026 March
  - Using different APIs: `sdmx` for ISTAT and `wbgapi` for World Bank
  - Update fertility stats with [2024 data released last October](https://www.istat.it/en/press-release/births-and-fertility-of-the-resident-population-year-2024/).
  
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

The following notes need to be updated for the new databases:
the best way to find the proper `dataset_id` is to browse [esploradati.istat.it](https://esploradati.istat.it/databrowser/#/en/dw/categories).

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