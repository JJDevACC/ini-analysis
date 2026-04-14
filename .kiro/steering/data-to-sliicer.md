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
- `pi_client.py` — PI Web API client (auth, server discovery, data retrieval via interpolated and summary endpoints)
- `csv_formatter.py` — Sliicer CSV formatting, hourly averaging with round-to-nearest-hour, unit conversion
- `sliicer_client.py` — ADS Prism Sliicer API client (Phase 3, not yet built)
- `main.py` — CLI orchestration script with --method, --units, --summary-type, --interval parameters
- `run_export.bat` — Main export batch launcher (single method run)
- `compare_methods.bat` — Runs both interpolated and PI summary methods for side-by-side comparison
- `test_connection.py` + `test_connection.bat` — Manual validation script for testing PI Web API calls
- `ai-questions.md` — Open questions for Craig / the ADS Prism team
- `api-call-comparison.md` — Detailed investigation of API call differences between Craig's R code and our Python code
- `examples/WES8617.csv`, `examples/BRA10477.csv` — Reference CSV files showing the target output format

## Critical Decision: Interpolated Method is the Default

### RESOLVED: Value matching with Craig's CSV
After extensive investigation, the interpolated method (`--method interpolated`) now produces values that match Craig's example CSV to 7-9 significant digits. The key fix was changing `compute_hourly_averages` from flooring timestamps to rounding to the nearest hour, matching R's `round_date("1h")` behavior.

### Why interpolated + round_date is used (not PI summary)
Craig's approach uses `round_date("1h")` which creates a **centered window** around each hour mark. The 1:00 AM value represents the average of data from 12:30 AM to 1:29 AM — the 30 minutes before and after the hour. This gives the flow rate that best represents what's happening "at" that hour.

The PI summary method (`--method summary`) uses a **trailing window** — it averages from the top of each hour to the top of the next (12:00 AM to 12:59 AM). This produces different values (3-20% different from Craig's).

**For Sliicer uploads, always use `--method interpolated` (the default in `run_export.bat`).** The PI summary method is available for comparison but should not be used for production Sliicer data unless confirmed acceptable.

### Unit conversion
PI tag `wes8617b_realtmmetflo` stores data in GPM (confirmed via PI Point metadata `"EngineeringUnits": "GPM"`). The `--units gpm-to-mgd` conversion (factor: 1440/1,000,000) is applied by default. Use `--units none` to skip conversion.

## Decisions Made During Implementation

### .env file location
Moved from `ini-analysis/.env` to `ini-analysis/data-to-sliicer/.env` so all sub-project files are co-located. Scripts use `dotenv` to load from the same directory as the script.

### Disregarded files
`ini-analysis/prism_flow_export.py` was written by a previous AI and is being disregarded. We are building fresh in `data-to-sliicer/`.

### Both PI Web API servers return identical data
Postman testing confirmed that `MASTERPIAPP` (production) and `masterpidvapp` (dev) return identical interpolated values for the same query. Both connect to the same underlying PI Data Archive (`masterpi`). Either server can be used.

### PI Web API timezone behavior
- Responses always return timestamps in UTC (ISO 8601 with Z suffix)
- Input times without timezone info are interpreted as the PI server's local time (EST/EDT)
- Our code converts UTC responses to local time via `.astimezone()` before hourly grouping
- Craig's R code does the same via `with_tz(ymd_hms(...), Sys.timezone())`

### InsecureRequestWarning suppression
When `PIWEBAPI_VERIFY_TLS=false`, `urllib3.disable_warnings(InsecureRequestWarning)` is called in `create_session()` to keep console output clean.

## PI Web API Details
- Production server: `https://MASTERPIAPP.corp.jea.com/piwebapi/`
- Dev server (in .env): `https://masterpidvapp.corp.jea.com/piwebapi`
- Auth: NTLM with service account credentials from .env
- Data server name: `masterpi` (configurable via `PIWEBAPI_SERVER` env var)
- Example PI tag: `wwl:south:wes8617b_realtmmetflo`
- Tag naming convention: `{system}:{area}:{siteid}{suffix}_realtmmetflo`
- Site ID derived from tag: `WES8617` from `wes8617b_realtmmetflo` (uppercase, strip trailing alpha before `_realtmmetflo`)
- Engineering units: GPM (gallons per minute), converted to MGD for Sliicer CSV

## Sliicer CSV Format
3-line header + hourly data rows. Same value repeated in 3 columns. 12-hour AM/PM timestamps. `#VALUE!` for error values. Windows line endings. See `examples/WES8617.csv` for the reference format.

## Phase Status
- Phase 1 (PI Web API data retrieval): COMPLETE — pi_client.py with 18 passing tests
- Phase 2 (CSV formatting + hourly averaging): COMPLETE — csv_formatter.py with tests
- Phase 2.5 (CLI + batch launcher): COMPLETE — main.py + run_export.bat + compare_methods.bat with tests
- Phase 3 (Sliicer API posting): NOT STARTED — task 8 in tasks.md (optional, endpoint unconfirmed)
- VALUE MATCHING MILESTONE: Interpolated method matches Craig's CSV to 7-9 significant digits
- Total: 67 tests passing across 3 test files

## Open Questions
See `data-to-sliicer/ai-questions.md` for the full list. Key unresolved items:
- What does `Average=None` mean in the CSV header?
- Are the three data columns always identical?
- Correct Sliicer API endpoint for posting flow data
- Site ID derivation convention across all sites
