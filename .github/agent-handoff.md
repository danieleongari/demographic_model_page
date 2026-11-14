# Current agent handoff

- **Status, 2026-11-14:** Added personal-home navigation to `index.html`, using
  the linked IPAB page's “← Home” / “← Back to Home” labels. The header retains
  its dark `#333` background and GitHub icon, with home on the left and GitHub
  on the right. Added a matching dark footer containing only the personal-home
  link. Both home links point to `https://www.italiancurious.com/`.
- Header/footer share an 800px navigation container, white link styling and
  keyboard focus indicators. Kept the existing header hide/reappear behavior
  and removed the old bottom spacer in favor of footer spacing. The footer has
  no GitHub link or file-modification timestamp. README and working guidance
  describe this navigation convention.
- Validation: checked header/footer link counts and destinations and all local
  asset references. Headless Chromium checks matching backgrounds, keyboard
  focus, navigation fit at 1024px and 390px, scroll hide/reappear, and JavaScript
  errors. Header/footer screenshots were inspected. Chart iframes and remote
  resources were blocked during this local presentation check; no analysis or
  data retrieval was needed. No commit, push or deployment requested for this
  change; the previous explicit no-push instruction remains in force.
- Previous work is committed as `075820a` (`improve update status and minor
  cleaning`): framed dated source summary, footer timestamp removal, matching
  interactive retirement-life chart styling, and English ISTAT link preference
  with the user's Italian fallback exception. Notebook 86's static PNG and all
  scientific trace values were retained. The nbmirror pre-commit hook may
  regenerate/stage mirrors and require a commit retry.
- Source-language detail: the English fertility release's heading/slug says
  “Year 2026”, but its final observations refer to 2025. Its publication date
  is 3 November 2026; the original Italian release was 21 October. No matching
  English base-2025 projection press release, 2020 census release, or historical
  methodology PDFs were found, so their Italian originals are retained.

## Carried-forward model and workflow

- Latest committed baseline: `fbf4bfe` (`add life expectation at retirement`).
  National inputs cover population through 1 January 2026 and mortality/final
  fertility through 2025; official projections are base-2025 through 2080.
  Official TFR 1.14 differs from the effective model coefficient 1.10972919.
  Nine 2100 population scenarios span 16.6–77.5 million. The retirement proxy
  keeps the 2.06 working-age/retirement-age reference ratio; the 1990 birth cohort
  spans retirement ages 67–72 (2057–2062). Economic, regional and international
  extensions remain future work.
- Maintained national runner: cached catalogue cells of `00`, then `14`, `30`,
  `40`, `45`, `63`, `70`, `73`, `84`, `86`, with execution offline and notebook
  exports via `nbmirror`. Supplementary `53` remains separate (`--heatwaves`);
  `20`/`25` and the exploration cells of `00` remain outside the chain.
- Notebook `84` exports `data/retirement_age_by_year.csv` (741 rows). Notebook
  `86_retiree_life_expectation.ipynb` consumes this and checked-in mortality CSVs,
  needs no raw snapshots/live access, and exports conditional **period** remaining
  life expectancy for 1974–2100 in all nine scenarios (719 annual/scenario rows).
  Effective retirement ages end in 2023; 2024–2026 assume age 64. Mortality is
  observed through 2025 and projected from 2026; scenario retirement ages begin
  in 2027. Use all single ages through 119, uniform within-age deaths, conditional
  fractional ages, and an analytic tail repeating q119. This differs deliberately
  from notebook `70`'s aggregate 100+ mortality assumption.
- Previous scientific validation: 36 tests and 13 national-model checks passed;
  see `data/refresh_validation.json`. This presentation edit did not rerun them.
  Notebook `86` outputs include annual/fixed-age CSVs, a method/provenance JSON,
  interactive HTML and PNG, and a notebook HTML export. At fixed age 65, remaining
  life is 21.4108 years in 2025 and 24.0204 in 2100; 2100 scenario retirement ages
  span 66–78 and remaining life 13.1164–23.1323 years. Use the existing
  `--from-notebook 84` or `--from-notebook 86` offline runner to regenerate.
- Supplementary `53` retains the 2002–2025 ERA5/Milan comparison from 11 November:
  direct weather-year/CCR-year alignment, zero-exposure years, signed correlations
  and COVID/2003 sensitivities. Its guarded Open-Meteo retrieval never calls ISTAT.
- **ISTAT access:** Follow `copilot-instructions.md` and `istat-access-audit.md`.
  Never exceed five API requests per rolling minute per public IP. Maintained
  retrieval is stricter: quiet minute, 30.1s after completion, bounded killable
  transport, no redirects/retries, shared persistent halt. Prefer checked-in
  inputs; raw sources, HTTP caches, `.venv` and bytecode stay ignored.
- **Standing VPN preference:** If an actual ISTAT request blocks/hangs, stop and
  ask the user to enable/check Surfshark Italy. Their confirmation authorizes one
  tiny guarded connection check after a quiet minute. A local halt alone is not
  proof of a provider block or reason to request VPN use. The authorized check
  on 11 November succeeded; after explicit continuation the precautionary halt
  was reviewed/cleared under lock, retaining counters/history. Its one-use
  authorization was consumed; no further live calls have followed.
