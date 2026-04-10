# Requirements Document

## Introduction

This feature automates the pipeline that a Water Wastewater Engineer currently performs manually: pulling flow data from an AVEVA PI system via PI Web API, formatting it into a specific CSV format required by ADS Prism Sliicer, and eventually posting the data to Sliicer via its API. The solution replaces existing R code with Python 3.12, is designed for incremental delivery, and targets eventual deployment on AWS Lambda.

## Glossary

- **PI_Web_API_Client**: The Python module responsible for authenticating with and making HTTP requests to the AVEVA PI Web API server using NTLM/Basic auth and credentials from environment variables.
- **PI_Point**: A named time-series tag in the AVEVA PI system (e.g., `wwl:south:wes8617b_realtmmetflo`) that records flow meter data.
- **Data_Server**: The PI Data Archive server (e.g., `masterpi`) that hosts PI Points and is discovered via the PI Web API `/dataservers` endpoint.
- **WebID**: A unique identifier returned by PI Web API for a PI Point, used to query stream data from the `/streamsets/interpolated` endpoint.
- **Interpolated_Data**: Time-series values returned by PI Web API at evenly-spaced intervals (e.g., every 1 minute) computed by the server from recorded values.
- **Hourly_Average**: A single flow value for each clock hour, computed by averaging the 1-minute Interpolated_Data samples that fall within that hour.
- **CSV_Formatter**: The Python module responsible for writing flow data rows into the ADS Prism Sliicer CSV format.
- **Sliicer_CSV**: The output CSV file conforming to the ADS Prism Sliicer import format with a 3-line header and hourly data rows.
- **Site_ID**: A station identifier derived from the PI_Point tag name (e.g., `WES8617` from `wes8617b_realtmmetflo`) used in the first line of the Sliicer_CSV header.
- **Sliicer_API_Client**: The Python module responsible for posting telemetry data to the ADS Prism Sliicer API endpoint (`POST /api/Telemetry`).
- **Pipeline_Runner**: The top-level orchestration script (and companion `.bat` file) that accepts command-line parameters and coordinates the PI_Web_API_Client, CSV_Formatter, and Sliicer_API_Client.
- **MGD**: Million Gallons per Day, the unit of measure for flow values in the Sliicer_CSV.

## Requirements

### Requirement 1: PI Web API Authentication and Connection

**User Story:** As a Water Wastewater Engineer, I want the Python pipeline to authenticate with PI Web API using credentials from a `.env` file, so that I do not have to hard-code or repeatedly enter credentials.

#### Acceptance Criteria

1. THE PI_Web_API_Client SHALL read `PIWEBAPI_URL`, `PIWEBAPI_USER`, `PIWEBAPI_PASS`, and `PIWEBAPI_VERIFY_TLS` from a `.env` file using the `python-dotenv` library.
2. WHEN `PIWEBAPI_VERIFY_TLS` is set to `false`, THE PI_Web_API_Client SHALL disable TLS certificate verification for all requests to PI Web API.
3. THE PI_Web_API_Client SHALL authenticate using the username and password from the `.env` file when making HTTP requests to PI Web API.
4. IF the `.env` file is missing or any required credential variable is absent, THEN THE PI_Web_API_Client SHALL raise a descriptive error message identifying the missing variable.
5. IF PI Web API returns an HTTP error status (4xx or 5xx), THEN THE PI_Web_API_Client SHALL raise an error that includes the HTTP status code and response body.

### Requirement 2: PI Point Discovery via Data Server

**User Story:** As a Water Wastewater Engineer, I want to look up a PI Point by its tag name, so that I can retrieve its WebID for subsequent data queries.

#### Acceptance Criteria

1. WHEN a PI_Point tag name is provided (e.g., `wwl:south:wes8617b_realtmmetflo`), THE PI_Web_API_Client SHALL query the PI Web API `/dataservers` endpoint to discover the Data_Server named `masterpi`.
2. WHEN the Data_Server is found, THE PI_Web_API_Client SHALL query the Data_Server's `/points?namefilter=` endpoint with the PI_Point tag name to retrieve the WebID.
3. IF the specified Data_Server name does not match any server returned by `/dataservers`, THEN THE PI_Web_API_Client SHALL raise an error stating the server was not found.
4. IF the PI_Point tag name does not match any point on the Data_Server, THEN THE PI_Web_API_Client SHALL raise an error stating the PI Point was not found.

### Requirement 3: Retrieve Interpolated Flow Data

**User Story:** As a Water Wastewater Engineer, I want to retrieve 1-minute interpolated flow data from PI Web API for a given PI Point and time range, so that I can compute hourly averages matching the existing R code behavior.

#### Acceptance Criteria

1. WHEN a WebID, start time, and end time are provided, THE PI_Web_API_Client SHALL request interpolated data from the PI Web API `/streamsets/interpolated` endpoint with an interval of `1m`.
2. THE PI_Web_API_Client SHALL pass `startTime`, `endTime`, and `interval` as query parameters along with the `webId` parameter.
3. THE PI_Web_API_Client SHALL parse each returned item's `Timestamp` (ISO 8601 format) and numeric `Value` into a list of timestamp-value pairs.
4. IF a returned item's `Value` is non-numeric (e.g., a digital state or error object), THEN THE PI_Web_API_Client SHALL exclude that item from the result list.
5. THE PI_Web_API_Client SHALL convert all returned timestamps to the local system timezone for downstream processing.

### Requirement 4: Compute Hourly Averages

**User Story:** As a Water Wastewater Engineer, I want the pipeline to compute hourly average flow values from 1-minute interpolated data, so that the output matches the existing R code behavior of `round_date("1h")` and `mean()`.

#### Acceptance Criteria

1. WHEN 1-minute Interpolated_Data is provided, THE Pipeline_Runner SHALL group the data points by clock hour (rounding each timestamp down to the nearest hour boundary).
2. THE Pipeline_Runner SHALL compute the arithmetic mean of all data points within each hourly group, excluding any missing or non-numeric values.
3. THE Pipeline_Runner SHALL produce one Hourly_Average value per clock hour, starting from the first full hour in the data range.
4. IF an entire hourly group contains only non-numeric or missing values, THEN THE Pipeline_Runner SHALL output `#VALUE!` for that hour in the Sliicer_CSV.

### Requirement 5: Format and Write Sliicer CSV

**User Story:** As a Water Wastewater Engineer, I want the pipeline to write flow data to a CSV file in the exact format required by ADS Prism Sliicer, so that I can import it without manual reformatting.

#### Acceptance Criteria

1. THE CSV_Formatter SHALL write line 1 as `{Site_ID},Average=None,QualityFlag=FALSE,QualityValue=FALSE`.
2. THE CSV_Formatter SHALL write line 2 as `DateTime,MP1\QFINAL,MP1\QCONTINUITY,MP1\QUANTITY`.
3. THE CSV_Formatter SHALL write line 3 as `MM/dd/yyyy h:mm:ss tt,MGD,MGD,MGD`.
4. THE CSV_Formatter SHALL write each data row with the timestamp formatted as 12-hour AM/PM format (e.g., `06/12/2024 12:00:00 AM`) followed by the same flow value repeated in all three data columns.
5. THE CSV_Formatter SHALL format numeric flow values as decimal numbers without trailing zeros (e.g., `2.184343173` not `2.184343170`).
6. WHEN a data point has no valid numeric value, THE CSV_Formatter SHALL write `#VALUE!` in all three data columns for that row.
7. THE CSV_Formatter SHALL use Windows-style line endings (`\r\n`) in the output file.

### Requirement 6: CSV Round-Trip Integrity

**User Story:** As a developer, I want to verify that the CSV writing and reading logic preserves data fidelity, so that no data is lost or corrupted during formatting.

#### Acceptance Criteria

1. FOR ALL valid lists of hourly timestamp-value pairs, writing to Sliicer_CSV and then parsing the Sliicer_CSV back SHALL produce an equivalent list of timestamp-value pairs (round-trip property).
2. THE CSV_Formatter SHALL preserve numeric precision to at least 9 significant digits for all flow values.

### Requirement 7: Command-Line Interface and Batch File

**User Story:** As a Water Wastewater Engineer, I want to run the pipeline from a `.bat` file with parameters for PI Point name, start time, end time, and calculation type, so that I can easily re-run exports without editing code.

#### Acceptance Criteria

1. THE Pipeline_Runner SHALL accept command-line arguments for: PI Point tag name, start time, end time, and calculation type (e.g., `average` or `interpolated`).
2. THE Pipeline_Runner SHALL accept an optional command-line argument for the output CSV file path, defaulting to `{Site_ID}.csv` in the current directory.
3. THE Pipeline_Runner SHALL derive the Site_ID from the PI Point tag name for use in the CSV header.
4. WHEN the calculation type is `average`, THE Pipeline_Runner SHALL retrieve 1-minute interpolated data and compute Hourly_Averages.
5. WHEN the calculation type is `interpolated`, THE Pipeline_Runner SHALL retrieve hourly interpolated data directly from PI Web API with a `1h` interval.
6. A companion `.bat` file SHALL invoke the Pipeline_Runner Python script with configurable parameters for PI Point tag name, start time, end time, and calculation type.

### Requirement 8: Post Telemetry to ADS Prism Sliicer API

**User Story:** As a Water Wastewater Engineer, I want the pipeline to post flow data directly to the ADS Prism Sliicer API, so that I no longer need to manually upload CSV files.

#### Acceptance Criteria

1. WHEN an API key is configured in the `.env` file (variable `SLIICER_API_KEY`), THE Sliicer_API_Client SHALL authenticate requests to the ADS Prism Sliicer API using that key.
2. WHEN the `--post-to-sliicer` flag is provided, THE Pipeline_Runner SHALL send the formatted telemetry data to the `POST /api/Telemetry` endpoint at `https://api.adsprism.com`.
3. IF the Sliicer API returns an HTTP error status, THEN THE Sliicer_API_Client SHALL raise an error that includes the HTTP status code and response body.
4. IF the `--post-to-sliicer` flag is provided without a configured `SLIICER_API_KEY`, THEN THE Pipeline_Runner SHALL raise a descriptive error stating the API key is missing.

### Requirement 9: Logging and Error Reporting

**User Story:** As a Water Wastewater Engineer, I want clear log output when the pipeline runs, so that I can diagnose issues without reading source code.

#### Acceptance Criteria

1. THE Pipeline_Runner SHALL log the PI Point tag name, time range, and calculation type at the start of each run.
2. WHEN the CSV file is written successfully, THE Pipeline_Runner SHALL log the output file path and the number of data rows written.
3. IF any step in the pipeline fails, THEN THE Pipeline_Runner SHALL log a descriptive error message including the failing step name and the underlying error details.
4. THE Pipeline_Runner SHALL use Python's standard `logging` module with a configurable log level (default: `INFO`).

### Requirement 10: Incremental Delivery Phases

**User Story:** As a developer, I want the feature built in incremental phases, so that each phase can be tested and validated independently before moving to the next.

#### Acceptance Criteria

1. THE Pipeline_Runner SHALL support Phase 1 (PI Web API data retrieval) as a standalone capability that outputs raw data to the console or a simple file.
2. THE Pipeline_Runner SHALL support Phase 2 (CSV formatting) as an addition to Phase 1 that writes the Sliicer_CSV file.
3. THE Pipeline_Runner SHALL support Phase 3 (Sliicer API posting) as an addition to Phase 2 that posts data to the ADS Prism Sliicer API.
4. EACH phase SHALL function independently of later phases (Phase 1 works without Phase 2 or 3; Phase 2 works without Phase 3).
