# AI Questions - Data to Sliicer Project

Open questions to clarify with the Water Wastewater Engineer or ADS Prism team.

## CSV Format Questions

### 1. What does `Average=None` mean in the CSV header?
The R code computes hourly averages (`round_date("1h")` + `mean()`), but the first line of the CSV header reads `WES8617,Average=None,QualityFlag=FALSE,QualityValue=FALSE`. Is `Average=None` a Sliicer-specific convention (e.g., telling Sliicer not to do additional averaging on import), or does it indicate the data was not averaged? Need to confirm whether this value should change based on how the data was computed.

### 2. Are the three data columns always identical?
Both example CSVs (`WES8617.csv` and `BRA10477.csv`) have the same value repeated across `MP1\QFINAL`, `MP1\QCONTINUITY`, and `MP1\QUANTITY` for every row. Is this always the case for all sites, or could these columns differ? For now we are assuming all three are always the same value.

## ADS Prism Sliicer API Questions

### 3. Confirm the correct API endpoint for posting flow data
The swagger spec at `https://api.adsprism.com/swagger/index.html` has a `POST /api/Telemetry` endpoint. Need to confirm this is the correct endpoint for uploading hourly flow data, and what the expected payload format is.

## PI Point / Site ID Questions

### 4. Site ID derivation from PI Point tag name
Currently assuming the site ID (used in the CSV header) is derived from the PI Point tag name by extracting the portion before the suffix (e.g., `WES8617` from `wes8617b_realtmmetflo`). Need to confirm this convention holds for all sites.

## Data Retrieval Method Questions

### 5. Server-side hourly averages vs. client-side averaging of 1-minute interpolated data
Craig's R code pulls 1-minute interpolated data and computes hourly averages client-side (`round_date("1h")` + `mean()`). PI Web API also supports server-side summaries via the `/streams/{webId}/summary` endpoint with `summaryType=Average` and `summaryDuration=1h`, which computes time-weighted averages directly on the server. The server-side approach is more efficient (24 values/day vs 1440) but may produce slightly different numbers since PI computes a time-weighted average from recorded data rather than an arithmetic mean of interpolated values. Need to confirm with Craig which approach produces the values Sliicer expects. For now, the Python code supports both methods via a `--method` parameter so we can compare outputs.

### 6. What are the native engineering units of the PI flow tags?
Our produced CSV values are roughly 650× larger than Craig's example CSV values for the same timestamps. We suspect the PI tag `wes8617b_realtmmetflo` stores data in GPM (gallons per minute) and Craig's output is in MGD (million gallons per day). The conversion factor GPM → MGD is `× 1440 / 1,000,000 = × 0.00144`. No unit conversion was found in Craig's R piwebapi library code — it may happen in a separate script we don't have, or the PI tag may have a built-in unit conversion. Need to confirm with Craig: (a) what are the native units of the flow PI tags, and (b) does he apply a conversion somewhere in his workflow that we're missing?
