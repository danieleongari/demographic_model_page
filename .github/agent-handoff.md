# Current agent handoff

- **Status, 2026-11-14:** Added and executed
  `notebooks/86_retiree_life_expectation.ipynb`. It plots remaining period life
  expectancy conditional on each calendar year's retirement age for 1974–2100,
  using notebook 30's observed ISTAT single-age death probabilities, notebook
  63's existing mortality projections, and all nine retirement-age paths from
  notebook 84. No live ISTAT or other data requests were made; two ONS methodology
  pages were read to verify the life-table interpretation. The user subsequently
  requested commit `add life expectation at retirement` and a push to
  `origin/main`; this handoff accompanies that commit. No separate deployment
  was requested.
- Publication preparation: reviewed all 19 staged files and fetched `origin/main`;
  local and remote main were aligned before committing. The installed nbmirror
  pre-commit hook regenerated and staged the two affected notebook mirrors,
  then required a commit retry. Its standard output retains six whitespace
  warnings in generated CSS comments/blank lines; source code is unaffected.
  Existing scientific validation remains applicable; no model code changed
  in this publication step.
- Notebook 84 now exports `data/retirement_age_by_year.csv` (741 rows): one
  historical/current row per population year and nine scenario rows in each
  future year. Its ratio search, assumptions, cell identities and saved numerical
  outputs are unchanged. After verifying all numerical outputs against HEAD,
  equivalent saved outputs and metadata were preserved to avoid random Plotly
  IDs and execution-timestamp churn. Its notebook HTML was regenerated.
- Notebook 86 uses 719 year/scenario records from 1974 onward. Effective
  retirement ages are the unweighted male/female mean of the digitized OECD
  series already embedded in 84, observed through 2023. The 2024–2026 age of 64
  is explicitly assumed. Mortality is observed through 2025, projected from
  2026. The nine retirement-age forecasts begin in 2027, after the January 2026
  population baseline. Source/assumption/projection status is kept in the CSVs
  and interactive hover. This is a representative-age, both-sex life table,
  not a sex-weighted estimate of actual pension entrants' mortality.
- The adult life table uses uniform deaths within each year of age, conditional
  fractional-age calculations, all single ages through 119, and an analytic
  open tail repeating q119 thereafter. This deliberately uses more detailed
  old-age mortality than notebook 70's aggregate 100+ bin (fixed 40% mortality).
  Forcing death within the final age interval changes the reported values by
  at most 1.05e-10 years. These are **period**, not cohort, expectancies; the
  selected year's mortality schedule stays fixed over the remaining lifetime.
  Future mortality is reused directly from 63, shared by all nine scenarios,
  without a new longevity fit or forced smooth join to 2025.
- Results: at fixed age 65, remaining life is 21.4108 years in 2025, 21.2393 in
  the first projected year 2026, and 24.0204 in 2100. The 2100 scenarios span
  retirement ages 66–78 and remaining life 13.1164–23.1323 years. Integer
  retirement-age changes create steps; some scenario lines overlap.
- Exports: `data/retiree_life_expectancy_by_year.csv`,
  `data/retiree_fixed_age_life_expectancy.csv` (127 annual fixed-age values),
  `data/retiree_life_expectancy_summary.json` (method, coverage, input hashes,
  optional local-source retrieval timestamp, tail sensitivity and results),
  `images_output/retiree_life_expectancy.html`,
  `images_output/retiree_life_expectancy.png`, and
  `notebooks_html/86_retiree_life_expectation.html`. The static figure includes
  a fixed-age-65 mortality comparison. `index.html` embeds the interactive chart
  and links the notebook/PNG; README and working guidance describe the method.
- Pure numerical functions and seven analytical/regression tests are in
  `scripts/retiree_life_expectancy.py` and
  `scripts/test_retiree_life_expectancy.py`. Checks cover geometric mortality,
  certain death, zero-mortality intervals, independent forward survival sums,
  fractional-age conditioning, mortality improvement, year/scenario alignment,
  and invalid inputs. The national validator checks annual scenario coverage,
  agreement with the existing 1990-cohort summary, annual/fixed-age expectancy,
  input hashes and end-year summary values.
- Maintained national execution chain: cached catalogue cells of `00`, then
  `14`, `30`, `40`, `45`, `63`, `70`, `73`, `84`, **`86`**, with HTTP disabled.
  `python scripts/refresh_model.py --from-notebook 84` rebuilds the retirement
  export and 86; `--from-notebook 86` reuses the export. The default final
  notebook is now 86, followed by validation. Supplementary 53 remains separate
  (`--heatwaves`); 20/25 and the exploration cells of 00 remain outside the chain.
- Validation: notebooks 84 and 86 executed offline with `nbmirror` exports;
  **36 tests and 13 national-model checks pass**. Latest report is
  `data/refresh_validation.json`. The national population/mortality inputs,
  reference ratio 2.06 and 1990-cohort retirement summary remain unchanged.
  The PNG was inspected visually; all 37 local links in the main page and the
  two affected notebook exports resolve; notebook schema/code and source
  whitespace checks pass. The later pre-commit regeneration is noted above. Browser preview was blocked because the browser security policy
  disallows local file URLs; no workaround was attempted. Interactive browser
  QA therefore remains uncompleted. Jupyter required approved local kernel
  sockets outside the sandbox; execution still disabled HTTP.
- National baseline remains: residents through 1 January 2026; mortality/final
  fertility through 2025; ISTAT base-2025 projections through 2080. Official TFR
  1.14 differs from the model's effective rate 1.10972919. Nine 2100 population
  scenarios span 16.6–77.5 million; the 1990 cohort's demographic retirement
  proxy spans ages 67–72 (2057–2062). Economic sustainability, regional and
  international extensions remain future work.
- Supplementary 53 remains the completed 2002–2025 ERA5/Milan comparison from
  11 November: correct weather-year/CCR-year alignment, zero-exposure years,
  signed correlations and COVID/2003 sensitivities. It uses its own guarded
  Open-Meteo retrieval and never calls ISTAT. Daily sources remain ignored.
- **ISTAT access:** Never exceed five requests per rolling minute per public
  IP; maintained retrieval is stricter (quiet minute, 30.1s after completion,
  bounded killable transport, no redirects/retries, shared persistent halt).
  Prefer checked-in inputs. Raw sources, HTTP caches, .venv and bytecode remain
  ignored. See `copilot-instructions.md` and `istat-access-audit.md`.
- **Standing VPN preference:** If an actual ISTAT request blocks/hangs, stop and
  ask the user to enable Surfshark Italy, or check/reconnect if already enabled.
  Confirmation authorizes one tiny guarded connectivity check after a quiet
  minute; do not ask twice or switch exits automatically. A local halt alone
  does not establish a provider block and is not a reason to request VPN use.
  The 11 November authorized check succeeded (HTTP 200, 1,577 bytes, 4.793s,
  ipsec0 routing). After explicit continuation, the precautionary halt was
  reviewed/cleared under lock while retaining counters/history; its one-use
  diagnostic authorization was consumed. No further live calls have followed.
