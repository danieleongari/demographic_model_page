# Demographic Model Page

Visualization: https://danieleongari.github.io/demographic_model_page/

Original project from deprecated https://github.com/danieleongari/saturdaymorningdsprojects, find the analysis in the `notebooks` folder of this repository.

Visualization posted on:

- [Linkedin (italian)](https://www.linkedin.com/posts/danieleongari_ho-preso-gli-ultimi-aggiornamenti-istat-e-activity-7181748786174586881-F5hI) - Apr24
- [Reddit r/ItaliaPersonalFinance](https://www.reddit.com/r/ItaliaPersonalFinance/comments/1bwcg3g/ho_preso_gli_ultimi_aggiornamenti_demografici/) - Apr24

## Notebooks

:chart with upward trend: Visualize the notebooks with interactive plotly graphs on [nbviewer](https://nbviewer.jupyter.org/github/danieleongari/demographic_model_page/tree/main/notebooks/).

- Exploring data
  - `available_istat_dataset` - explore how the istat_api package works, what can be the relevant dataset I need, and their structure
  - `investigate_italian_residents` - explore datasets for registered residents in Italy: `DCIS_RICPOPRES2011` and `DCIS_POPRES1`
  - `investigate_italian_deaths` - compare datasets `DCIS_MORTALITA1` and `DCIS_DECESSI` to spot the differences
  - `compare_deaths_deltaresidents` - compare deaths with the change in residents to spot the migration balance
  - `investigate_italian_deathprob` - spot trents in mortality over the years of observation, since 1974
  - `investigate_italian_fertility` - explore dataset `DCIS_FECONDITA1` and reconcile data with the population dataset 
  - `investigate_italian_migrations` - explore dataset `DCIS_MIGRAZIONI` and reconcile data with the population dataset
- Analyzing data
  - `correlate_deaths_heathwaves_2003` - correlate deaths with heatwaves to spot the bump in mortality in 2003
- Making predictions
  - `modelling_future_population` - predict future population based on past data and several extreme assumptions (scenarios)
  - `sustainable_retirement_age` - compute, for each generation, the retirement age to keep a consistent ratio of workers/retired

## ChengeLog

- 2025 January
  - Compared mortality from `DCIS_MORTALITA1` and `DCIS_DECESSI` and opened [a ticket to ISTAT for clarification](https://contact.istat.it/s/case/500Tj00000GdztvIAB)
  - Compared deaths with change-in-population, and obtained some qualitative results (not quantitative, as I can not use deaths data directly)
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
  - Published on [Linkedin](https://www.linkedin.com/feed/update/urn:li:activity:7051629734937411584/)