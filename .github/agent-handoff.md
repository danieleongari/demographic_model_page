# Current agent handoff

- **2026-11-11:** Moved all agent rules, the repository map, and planned-extension
  guidance into `copilot-instructions.md` in this directory. Reduced root
  `AGENTS.md` to a redirect and moved the handoff here. Updated the README pointer
  and maintenance rules to use these locations.
- Validation: checked local Markdown links, rule preservation, and whitespace;
  no ISTAT calls or notebook executions were needed for this documentation change.
- Remaining: live retrieval is not centrally rate-limited by this documentation.
  Audit and enforce throttling before any future live execution. Some exploratory
  notebooks still import legacy `istatapi`, and notebook `40` imports `wbgapi`,
  which is absent from the requirements file; account for this if running them.
