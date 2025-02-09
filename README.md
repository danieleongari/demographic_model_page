# Demographic Model Page

🌐 https://danieleongari.github.io/demographic_model_page/

🔗 Original project from deprecated https://github.com/danieleongari/saturdaymorningdsprojects.

🗣️ Posted on:

- [Linkedin (Italian)](https://www.linkedin.com/posts/danieleongari_i-was-born-in-1990-and-i-will-retire-in-italy-activity-7051629734937411584-eDWZ) - 2023, April
- [Linkedin (italian)](https://www.linkedin.com/posts/danieleongari_ho-preso-gli-ultimi-aggiornamenti-istat-e-activity-7181748786174586881-F5hI) - 2024, April
- [Reddit r/ItaliaPersonalFinance](https://www.reddit.com/r/ItaliaPersonalFinance/comments/1bwcg3g/ho_preso_gli_ultimi_aggiornamenti_demografici/) - 2024, April

## Notebooks

📈 Visualize the notebooks with interactive plotly graphs on [nbviewer](https://nbviewer.jupyter.org/github/danieleongari/demographic_model_page/tree/main/notebooks/).

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