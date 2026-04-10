---
inclusion: fileMatch
fileMatchPattern: "data-to-sliicer/**"
---

# PI to Sliicer Automation — Project Steering

## Project Overview
Automating the pipeline that pulls flow data from AVEVA PI Web API and delivers it to ADS Prism Sliicer. Replaces a manual R-based workflow with Python 3.12. Spec lives at `.kiro/specs/pi-to-sliicer-automation/`.

## Working Directory
All code for this sub-project lives in `ini-analysis/data-to-sliicer/`. Do not place project files outside this folder.

## Environment and Tooling
- Python virtual environment: `ini-analysis/.venv` (Python 3.12)
- All pip installs MUST target this venv: `.venv/Scripts/pip install <package>`
- Run tests with: `.venv/Scripts/python -m pytest data-to-sliicer/tests/ -v` (from `ini-analysis/`)
- The `.env` file lives at `ini-analysis/data-to-sliicer/.env` (was moved from `ini-analysis/.env`)
- Key packages installed: requests, requests-ntlm, python-dotenv, hypothesis, pytest

## Key Files
- `pi_client.py` — PI Web API client (auth, server discovery, data retrieval)
- `csv_formatter.py` — Sliicer CSV formatting (Phase 2, not yet built)
- `sliicer_client.py` — ADS Prism Sliicer API client (Phase 3, not yet built)
- `main.py` — CLI orchestration script (not yet built)
- `test_connection.py` + `test_connection.bat` — Manual validation script for testing PI Web API calls
- `ai-questions.md` — Open questions for Craig / the ADS Prism team
- `examples/WES8617.csv`, `examples/BRA10477.csv` — Reference CSV files showing the target output format

## Decisions Made During Implementation

### .env file location
Moved from `ini-analysis/.env` to `ini-analysis/data-to-sliicer/.env` so all sub-project files are co-located. Scripts use `dotenv` to load from the same directory as the script.

### Disregarded files
`ini-analysis/prism_flow_export.py` was written by a previous AI and is being disregarded. We are building fresh in `data-to-sliicer/`.

### Data retrieval methods
`pi_client.py` supports two approaches for getting flow data:
1. `get_interpolated_data()` — pulls data at a fixed interval (e.g. 1m) from `/streamsets/interpolated`. This matches Craig's R code behavior.
2. `get_summary_data()` — gets server-side computed summaries (e.g. hourly Average) from `/streams/{webId}/summary`. More efficient, but produces time-weighted averages which may differ slightly from the R code's arithmetic mean of interpolated values.

The user prefers server-side summary (Average) as the default for now, but wants both methods available via CLI parameters so outputs can be compared. See ai-questions.md question #5.

### InsecureRequestWarning suppression
When `PIWEBAPI_VERIFY_TLS=false`, `urllib3.disable_warnings(InsecureRequestWarning)` is called in `create_session()` to keep console output clean.

### Manual validation pattern
`test_connection.py` + `test_connection.bat` is the pattern for hands-on testing against the live PI Web API. The bat file has editable variables at the top (TAG, START, END, METHOD, INTERVAL, SUMMARY_TYPE). Output goes to `data-to-sliicer/output/` as JSON files.

## PI Web API Details
- Production server: `https://MASTERPIAPP.corp.jea.com/piwebapi/`
- Dev server (in .env): `https://masterpidvapp.corp.jea.com/piwebapi`
- Auth: NTLM with service account credentials from .env
- Data server name: `masterpi` (configurable via `PIWEBAPI_SERVER` env var)
- Example PI tag: `wwl:south:wes8617b_realtmmetflo`
- Tag naming convention: `{system}:{area}:{siteid}{suffix}_realtmmetflo`
- Site ID derived from tag: `WES8617` from `wes8617b_realtmmetflo` (uppercase, strip trailing alpha before `_realtmmetflo`)

## Sliicer CSV Format
3-line header + hourly data rows. Same value repeated in 3 columns. 12-hour AM/PM timestamps. `#VALUE!` for error values. Windows line endings. See `examples/WES8617.csv` for the reference format.

## Phase Status
- Phase 1 (PI Web API data retrieval): COMPLETE — pi_client.py with 18 passing tests
- Phase 2 (CSV formatting + hourly averaging): COMPLETE — csv_formatter.py with 21 passing tests
- Phase 2.5 (CLI + batch launcher): COMPLETE — main.py + run_export.bat with 27 passing tests
- Phase 3 (Sliicer API posting): NOT STARTED — task 8 in tasks.md (optional, endpoint unconfirmed)
- Total: 66 tests passing across 3 test files

## Open Questions
See `data-to-sliicer/ai-questions.md` for the full list. Key unresolved items:
- What does `Average=None` mean in the CSV header?
- Are the three data columns always identical?
- Correct Sliicer API endpoint for posting flow data
- Site ID derivation convention across all sites
- Server-side vs client-side averaging — which does Sliicer expect?
