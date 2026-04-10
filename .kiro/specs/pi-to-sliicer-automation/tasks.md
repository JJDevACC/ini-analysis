# Implementation Plan: PI to Sliicer Automation

## Overview

Incremental Python 3.12 pipeline built in three phases inside `ini-analysis/data-to-sliicer/`. Phase 1 pulls data from PI Web API, Phase 2 writes Sliicer-compatible CSVs, Phase 3 (optional) posts telemetry to the ADS Prism Sliicer API. All code uses `requests`, `requests-ntlm`, `python-dotenv`, and Python stdlib. Tests use `pytest` + `hypothesis`.

## Tasks

- [x] 1. Project scaffolding and configuration loader
  - [x] 1.1 Create `ini-analysis/data-to-sliicer/pi_client.py` with module docstring, imports (`requests`, `requests_ntlm`, `datetime`, `logging`), and the `create_session` function that reads `PIWEBAPI_URL`, `PIWEBAPI_USER`, `PIWEBAPI_PASS`, `PIWEBAPI_VERIFY_TLS` from the environment (loaded via `python-dotenv` from `ini-analysis/.env`), validates all four are present (raising `ValueError` naming missing vars), creates a `requests.Session` with `HttpNtlmAuth`, and sets `verify` based on `PIWEBAPI_VERIFY_TLS`.
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 1.2 Create `ini-analysis/data-to-sliicer/tests/` directory with an empty `__init__.py` and `test_pi_client.py` containing a smoke test that imports `pi_client` successfully.
    - _Requirements: 10.1_

  - [x] 1.3 Write property test for missing environment variable error (Property 9)
    - **Property 9: Missing Environment Variable Error**
    - For any non-empty subset of required env vars that is absent, `create_session` raises a `ValueError` whose message names at least one missing variable.
    - Add test to `tests/test_pi_client.py` using `hypothesis` with `@given(st.sets(st.sampled_from([...]), min_size=1))`.
    - **Validates: Requirements 1.4**

- [x] 2. Phase 1 — PI Web API data retrieval
  - [x] 2.1 Implement `find_data_server(session, base_url, server_name)` in `pi_client.py`
    - GET `/dataservers`, iterate `Items`, case-insensitive match on `Name`, return `WebId`.
    - Raise `ValueError` if not found. Raise on HTTP errors with status code + body.
    - _Requirements: 2.1, 2.3, 1.5_

  - [x] 2.2 Implement `find_point_webid(session, base_url, server_webid, tag_name)` in `pi_client.py`
    - GET `/dataservers/{webid}/points?namefilter={tag}`, return first match's `WebId`.
    - Raise `ValueError` if no match. Raise on HTTP errors with status code + body.
    - _Requirements: 2.2, 2.4, 1.5_

  - [x] 2.3 Implement `get_interpolated_data(session, base_url, web_id, start_time, end_time, interval)` in `pi_client.py`
    - GET `/streamsets/interpolated` with query params `webId`, `startTime`, `endTime`, `interval`.
    - Parse response JSON: iterate `Items[0].Items`, filter out non-numeric `Value` fields, parse ISO 8601 `Timestamp` to local-timezone `datetime`, return `list[tuple[datetime, float]]`.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 2.4 Write property test for non-numeric value filtering (Property 4)
    - **Property 4: Non-Numeric Value Filtering**
    - For any PI Web API response containing a mix of numeric and non-numeric Value fields, the parsed output contains exactly the numeric items with correct typing.
    - Add test to `tests/test_pi_client.py` using `hypothesis` to generate mixed response payloads.
    - **Validates: Requirements 3.3, 3.4**

  - [x] 2.5 Write property test for timestamp timezone conversion (Property 5)
    - **Property 5: Timestamp Timezone Conversion**
    - For any ISO 8601 UTC timestamp, the converted local datetime represents the same instant (round-trip to UTC yields original).
    - Add test to `tests/test_pi_client.py`.
    - **Validates: Requirements 3.5**

  - [x] 2.6 Write property test for data server not found error (Property 11)
    - **Property 11: Data Server Not Found Error**
    - For any list of server names not containing the target (case-insensitive), `find_data_server` raises `ValueError`.
    - Add test to `tests/test_pi_client.py`.
    - **Validates: Requirements 2.3**

  - [x] 2.7 Write property test for HTTP error propagation (Property 10)
    - **Property 10: HTTP Error Propagation**
    - For any HTTP response with 4xx/5xx status, the client raises an error containing both the status code and response body text.
    - Add test to `tests/test_pi_client.py` using mocked responses.
    - **Validates: Requirements 1.5, 8.3**

  - [x] 2.8 Write unit tests for PI client functions
    - Test `find_data_server` with mocked `/dataservers` response (happy path + not found).
    - Test `find_point_webid` with mocked points response (happy path + not found).
    - Test `get_interpolated_data` with mocked interpolated response including digital states.
    - Add tests to `tests/test_pi_client.py`.
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.3, 3.4_

- [x] 3. Checkpoint — Phase 1 validation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Phase 2 — CSV formatting and hourly averaging
  - [x] 4.1 Create `ini-analysis/data-to-sliicer/csv_formatter.py` with `derive_site_id(tag_name)` function
    - Extract site ID from PI tag name (e.g., `wwl:south:wes8617b_realtmmetflo` → `WES8617`). Uppercase, strip trailing alpha suffix before `_realtmmetflo`.
    - _Requirements: 7.3_

  - [x] 4.2 Implement `compute_hourly_averages(data)` in `csv_formatter.py`
    - Group `list[tuple[datetime, float]]` by clock hour (floor to hour boundary), compute arithmetic mean per group. Return `list[tuple[datetime, float | None]]` — `None` for hours with no valid data.
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 4.3 Implement `format_timestamp(dt)`, `format_value(value)`, and `write_sliicer_csv(file_path, site_id, rows)` in `csv_formatter.py`
    - `format_timestamp`: `MM/dd/yyyy h:mm:ss tt` 12-hour AM/PM format.
    - `format_value`: decimal string without trailing zeros, or `#VALUE!` for `None`.
    - `write_sliicer_csv`: write 3-line header + data rows with `\r\n` line endings, value repeated in 3 columns. Return row count.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 4.4 Implement `parse_sliicer_csv(file_path)` in `csv_formatter.py`
    - Parse a Sliicer CSV back into `list[tuple[datetime, float | None]]` for round-trip verification.
    - _Requirements: 6.1_

  - [x] 4.5 Create `tests/test_csv_formatter.py` with unit tests
    - Test `derive_site_id` with known tag names from examples.
    - Test `format_timestamp` with midnight, noon, AM/PM boundaries.
    - Test `format_value` with floats and `None`.
    - Test `write_sliicer_csv` header lines match exactly against `examples/WES8617.csv`.
    - Test `compute_hourly_averages` with known data from example CSVs.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 7.3_

  - [x] 4.6 Write property test for CSV round-trip (Property 1)
    - **Property 1: CSV Round-Trip**
    - For any valid list of hourly (datetime, float|None) pairs, write → parse produces equivalent data (timestamps match to minute, values match to 9 significant digits).
    - Add test to `tests/test_csv_formatter.py` using `hypothesis` with `tempfile`.
    - **Validates: Requirements 6.1, 6.2**

  - [x] 4.7 Write property test for hourly grouping structure (Property 2)
    - **Property 2: Hourly Grouping Structure**
    - For any list of 1-minute data spanning N distinct clock hours, `compute_hourly_averages` produces exactly N entries, one per hour.
    - Add test to `tests/test_csv_formatter.py`.
    - **Validates: Requirements 4.1, 4.3**

  - [x] 4.8 Write property test for hourly average value (Property 3)
    - **Property 3: Hourly Average Value**
    - For any list of 1-minute values within the same clock hour, `compute_hourly_averages` returns a single entry equal to the arithmetic mean.
    - Add test to `tests/test_csv_formatter.py`.
    - **Validates: Requirements 4.2**

  - [x] 4.9 Write property test for data row format (Property 6)
    - **Property 6: Data Row Format**
    - For any (datetime, float) pair, the formatted CSV row has 12-hour AM/PM timestamp + same value in 3 comma-separated columns.
    - Add test to `tests/test_csv_formatter.py`.
    - **Validates: Requirements 5.4**

  - [x] 4.10 Write property test for numeric formatting fidelity (Property 7)
    - **Property 7: Numeric Formatting Fidelity**
    - For any float with up to 9 significant digits, `format_value` produces a string with no trailing zeros, and parsing back recovers the value to 9 significant digits.
    - Add test to `tests/test_csv_formatter.py`.
    - **Validates: Requirements 5.5, 6.2**

  - [x] 4.11 Write property test for site ID derivation (Property 8)
    - **Property 8: Site ID Derivation**
    - For any tag name following `{prefix}:{location}:{siteid}{suffix}_realtmmetflo`, `derive_site_id` returns the uppercase site ID portion.
    - Add test to `tests/test_csv_formatter.py`.
    - **Validates: Requirements 7.3**

- [x] 5. Checkpoint — Phase 2 validation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. CLI orchestration and batch launcher
  - [x] 6.1 Create `ini-analysis/data-to-sliicer/main.py` with `argparse` CLI
    - Positional args: `tag`, `start`, `end`. Optional: `--calc-type` (default `average`), `--output`, `--post-to-sliicer`, `--log-level` (default `INFO`).
    - Load `.env` from `ini-analysis/.env` using `python-dotenv`.
    - Configure `logging` with the specified level.
    - Log tag name, time range, and calc type at start.
    - _Requirements: 7.1, 7.2, 9.1, 9.4_

  - [x] 6.2 Wire Phase 1 + Phase 2 into `main.py` pipeline
    - Call `create_session`, `find_data_server`, `find_point_webid`, `get_interpolated_data`.
    - If `--calc-type average`: call `compute_hourly_averages` on the 1-minute data.
    - If `--calc-type interpolated`: call `get_interpolated_data` with `interval="1h"` directly.
    - Call `derive_site_id`, `write_sliicer_csv`. Log output path and row count.
    - Wrap in try/except: log errors via `logging.error()`, exit with non-zero status.
    - _Requirements: 7.3, 7.4, 7.5, 9.2, 9.3, 10.1, 10.2_

  - [x] 6.3 Create `ini-analysis/data-to-sliicer/run_export.bat`
    - Accept `%1` (tag), `%2` (start), `%3` (end), `%4` (calc_type, default `average`).
    - Invoke `python main.py` with the parameters.
    - _Requirements: 7.6_

  - [x] 6.4 Write unit tests for CLI and orchestration in `tests/test_main.py`
    - Test argparse configuration (required args, defaults, optional flags).
    - Test pipeline wiring with mocked PI client and CSV formatter.
    - Test error handling: missing env vars, PI API errors, file write errors.
    - _Requirements: 7.1, 7.2, 9.1, 9.3_

- [x] 7. Checkpoint — Phase 1 + Phase 2 end-to-end validation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Phase 3 (OPTIONAL) — Sliicer API posting
  - [ ] 8.1 Create `ini-analysis/data-to-sliicer/sliicer_client.py` with `post_telemetry(api_key, site_id, rows, base_url)` function
    - POST to `/api/Telemetry` with API key auth. Raise on HTTP errors with status code + body.
    - Raise `ValueError` if `SLIICER_API_KEY` is missing when invoked.
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ] 8.2 Wire Phase 3 into `main.py`
    - When `--post-to-sliicer` flag is set: read `SLIICER_API_KEY` from env, call `post_telemetry` after CSV write. Log success/failure.
    - If flag is set but key is missing, raise `ValueError` with descriptive message.
    - _Requirements: 8.1, 8.2, 8.4, 10.3, 10.4_

  - [ ] 8.3 Write unit tests for Sliicer client in `tests/test_main.py`
    - Test `post_telemetry` with mocked HTTP responses (success, 4xx, 5xx).
    - Test missing API key error.
    - _Requirements: 8.1, 8.3, 8.4_

- [ ] 9. Final checkpoint — Full pipeline validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Phase 3 tasks (task 8) are marked as implementation tasks but the Sliicer API endpoint hasn't been confirmed yet — implement as a stub if needed
- Each task references specific requirements for traceability
- Property tests validate the 11 correctness properties defined in the design document
- All PI Web API calls are mocked in tests — no live API calls required
- The `.env` file at `ini-analysis/.env` already exists and should not be overwritten
