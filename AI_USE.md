# AI_USE.md: AI-use disclosure (42.510 course rule)

| Date | Tool | Purpose | Representative prompt | What the team independently checked |
|---|---|---|---|---|
| 22 Nov 2026 | Antigravity coding agent (connected to the Notion Mission Control page) | Read the task list; wrote the modelling code (`src/`, `analysis/`), the report draft, the slides draft and the guides; ran the validation pipeline on week 6 | "Pull all tasks from Mission Control and execute them; organise the folder with step-by-step instructions; prepare the presentation." | *To fill in by the team:* the self-tests rerun (`run_all.ps1`); each line of code read and understood; numbers in the report traced to `results/`; references opened |
| 22 Nov 2026 | Claude (Claude Code desktop app, used by Joanna) | Reviewed the repo against the proposal and decision log; found that the weather snapshot was one hour off (API returned a fixed GMT-5 clock during EDT) and fixed `01_weather_snapshot.py`; fixed alert-budget tie-breaking in `src/metrics.py`; stopped `run_all.ps1` overwriting the snapshot; reran steps 01-05 and 07 (valid); updated the report draft numbers and rebuilt the slides | "Check the materials in our GitHub repo and correct them if needed." | *To fill in by Joanna:* compared the old and new weather files against a UTC query; checked the new numbers in the report against `results/` |

Notes
- No raw Citi Bike trip files were uploaded to the AI. The AI worked only on the aggregated station-hour table already in the repository and on the public Open-Meteo weather series.
- The test weeks (13 to 26 Oct 2025) were **not** scored by the AI. The test script is locked until after the plan freeze.
- Every member must be able to explain and change every line. The team, not the AI, is responsible for errors.
