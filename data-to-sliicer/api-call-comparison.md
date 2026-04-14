# API Call Comparison: Craig's R Code vs Our Python Code

## IMPORTANT FINDING: Different PI Servers

Craig's R code hardcodes the **production** server in two places:
- `get_webid.R` line 14: `servername = "https://MASTERPIAPP.corp.jea.com/piwebapi/"`
- `get_tags.R` line 2: `PI_HOST_NAME = "MASTERPIAPP.corp.jea.com/piwebapi/"`

Our `.env` points to the **dev** server:
- `PIWEBAPI_URL=https://masterpidvapp.corp.jea.com/piwebapi`

**This alone could explain the value differences.** The dev and production PI servers may have different data.

---

## Craig's R Code — Full API Call Chain

### Step 1: Discover Data Server
**Function:** `get_webid()` → `get_dataserver()` → `get_url()`

```
GET https://MASTERPIAPP.corp.jea.com/piwebapi/dataservers/
Headers:
  X-Requested-With: PIWebApiWrapper
  Accept: application/xml;
Auth: gssnegotiate (Kerberos)
SSL Verify: false
```

Response: list of data servers. Finds "masterpi" by name (case-insensitive), gets its `WebId`.

### Step 2: Find PI Point WebID
**Function:** `get_webid()` → `get_dataserver()` → `get_url()`

```
GET https://MASTERPIAPP.corp.jea.com/piwebapi/dataservers/{SERVER_WEBID}/points?namefilter=wwl:south:wes8617b_realtmmetflo
Headers:
  X-Requested-With: PIWebApiWrapper
  Accept: application/xml;
Auth: gssnegotiate (Kerberos)
SSL Verify: false
```

Response: PI Point details including `WebId`.

### Step 3: Get Interpolated Data
**Function:** `get_sampled_multi()` → `get_sampled()` → `get_tags()`

Craig's R code calls `get_sampled_multi` with `freq="1m"` (the default). This function splits the time range into chunks to stay under the 135,000 item limit, then calls `get_sampled()` for each chunk, which calls `get_tags()`.

```
GET https://MASTERPIAPP.corp.jea.com/piwebapi/streamsets/interpolated
Query params:
  webId={POINT_WEBID}
  startTime={chunk_start}    (e.g. "2024-06-12")
  endTime={chunk_end}        (e.g. "2024-07-16" — ~93 days max per chunk for 1 tag)
  interval=1m
Headers:
  X-Requested-With: PIWebApiWrapper
  Accept: application/xml;
Auth: gssnegotiate (Kerberos)
SSL Verify: false
```

**Note:** The R code uses `scheme="https"`, `hostname=`, and `path="/interpolated"` separately in `httr::GET()`, which constructs the URL as:
`https://MASTERPIAPP.corp.jea.com/piwebapi/streamsets/interpolated?webId=...&startTime=...&endTime=...&interval=1m`

### Step 4: Client-Side Processing (R)
After getting 1-minute interpolated data, Craig's R code does:
```r
tmp %>%
  mutate(datehour=round_date(datetime, "1h")) %>%
  group_by(datehour) %>%
  summarize(q=mean(wwl.South.WES8617B_REALTMMETFLO, na.rm=TRUE))
```

This:
1. Rounds each timestamp to the nearest hour (`round_date` — note: this rounds, not floors)
2. Groups by the rounded hour
3. Computes arithmetic mean, ignoring NAs

**Key detail:** `round_date("1h")` rounds to the NEAREST hour, not floors. So a value at 12:31 would round to 1:00 PM, not 12:00 PM. Our Python code uses `replace(minute=0)` which floors. This could cause differences at hour boundaries.

---

## Our Python Code — Full API Call Chain

### Method A: Interpolated (matching Craig's approach)

#### Step 1: Discover Data Server
```
GET https://masterpidvapp.corp.jea.com/piwebapi/dataservers
Auth: NTLM (CORP\svcPiPostDev)
SSL Verify: false
```

#### Step 2: Find PI Point WebID
```
GET https://masterpidvapp.corp.jea.com/piwebapi/dataservers/{SERVER_WEBID}/points?namefilter=wwl:south:wes8617b_realtmmetflo
Auth: NTLM
SSL Verify: false
```

#### Step 3: Get Interpolated Data
```
GET https://masterpidvapp.corp.jea.com/piwebapi/streamsets/interpolated?webId={POINT_WEBID}&startTime=2024-06-12&endTime=2024-09-10&interval=1m
Auth: NTLM
SSL Verify: false
```

**Note:** We do NOT chunk the request like Craig's R code does. We send the full date range in one request. This could be an issue if the response exceeds PI Web API's max item limit.

#### Step 4: Client-Side Processing (Python)
```python
# Floor each timestamp to the hour (not round like R)
hour_key = ts.replace(minute=0, second=0, microsecond=0)
# Group and compute arithmetic mean
```

### Method B: PI Summary

#### Steps 1-2: Same as above

#### Step 3: Get Summary Data
```
GET https://masterpidvapp.corp.jea.com/piwebapi/streams/{POINT_WEBID}/summary?startTime=2024-06-12&endTime=2024-09-10&summaryType=Average&summaryDuration=1h
Auth: NTLM
SSL Verify: false
```

---

## Key Differences Summary

| Aspect | Craig's R Code | Our Python Code |
|--------|---------------|-----------------|
| **PI Server** | `MASTERPIAPP` (production) | `masterpidvapp` (dev) |
| **Auth** | Kerberos (gssnegotiate) | NTLM |
| **Accept Header** | `application/xml;` | (default — `application/json`) |
| **API Endpoint** | `/streamsets/interpolated` | `/streamsets/interpolated` (same) |
| **Interval** | `1m` | `1m` (same) |
| **Chunking** | Yes (~93 day chunks) | No (single request) |
| **Hour grouping** | `round_date("1h")` (rounds) | `replace(minute=0)` (floors) |
| **Non-numeric handling** | `as.numeric()` → NA, then `na.rm=TRUE` | Filter out before averaging |

## Postman Test URLs

To test in Postman, use these URLs with NTLM auth. Replace `{SERVER_WEBID}` and `{POINT_WEBID}` with actual values from Steps 1-2.

### Against Production (Craig's server)
```
GET https://MASTERPIAPP.corp.jea.com/piwebapi/dataservers
GET https://MASTERPIAPP.corp.jea.com/piwebapi/dataservers/{SERVER_WEBID}/points?namefilter=wwl:south:wes8617b_realtmmetflo
GET https://MASTERPIAPP.corp.jea.com/piwebapi/streamsets/interpolated?webId={POINT_WEBID}&startTime=2024-06-12T00:00:00Z&endTime=2024-06-12T02:00:00Z&interval=1m
```

### Against Dev (our server)
```
GET https://masterpidvapp.corp.jea.com/piwebapi/dataservers
GET https://masterpidvapp.corp.jea.com/piwebapi/dataservers/{SERVER_WEBID}/points?namefilter=wwl:south:wes8617b_realtmmetflo
GET https://masterpidvapp.corp.jea.com/piwebapi/streamsets/interpolated?webId={POINT_WEBID}&startTime=2024-06-12T00:00:00Z&endTime=2024-06-12T02:00:00Z&interval=1m
```

Use a short 2-hour window (midnight to 2AM on 06/12/2024) so the response is small enough to compare values manually.

### Auth for Postman
- Type: NTLM
- Username: `CORP\svcPiPostDev`
- Password: (from .env)
- Disable SSL verification in Postman settings

---

## Postman Test Results (2026-04-14)

### Finding 1: Both PI Web API servers return identical data
The interpolated data from `MASTERPIAPP` (production) and `masterpidvapp` (dev) is **value-for-value identical** for the same query. Both PI Web API instances connect to the same underlying PI Data Archive (`masterpi`, WebId `F1DSAAAAAAAAAAAAAAAAAAAdogTUFTVEVSUEk`). The server difference is **not** the cause of the value discrepancy.

### Finding 2: PI Point confirmed as GPM
The PI Point metadata from both servers confirms:
- `"EngineeringUnits": "GPM"`
- `"Span": 5000.0`
- `"PointType": "Float32"`

### Finding 3: PI Web API timezone behavior (from documentation)
Per the PI Web API reference:
- **On output:** PI Web API **always** returns timestamps as ISO 8601 UTC strings (with `Z` suffix)
- **On input:** If you pass a time without timezone info (e.g. `"2024-06-12"`), it is resolved relative to the **backend PI server's timezone** — not the client's timezone, and not the PI Web API server's timezone
- If you pass ISO 8601 with offset (e.g. `"2024-06-12T00:00:00Z"` or `"2024-06-12T00:00:00-04:00"`), it's used as-is

Since the PI server is in EST, passing `"2024-06-12"` without a timezone means PI interprets it as `2024-06-12 00:00:00 EST` = `2024-06-12T05:00:00Z`.

### Finding 4: Craig's R code passes dates without timezone
Craig's R code does:
```r
tmp <- piwebapi::get_sampled_multi(tags, ymd(today())-days(5), ymd(today()))
```
The `ymd(today())-days(5)` produces a lubridate date object like `2024-06-12`. When this gets passed to `get_tags()` as `startTime`, R's `httr::GET()` serializes it as a plain date string without timezone info. PI Web API then interprets it as **PI server local time (EST)**.

### Finding 5: Our Postman test used UTC timestamps
In the Postman test, we passed `startTime=2024-06-12T00:00:00Z` (explicit UTC). This means our query window started at midnight UTC = 8:00 PM EST on June 11th. Craig's query with `startTime=2024-06-12` would start at midnight EST = 4:00 AM UTC on June 12th.

**This is a 4-hour offset in the data window**, which would cause different values to fall into different hourly buckets when averaging.

### Finding 6: Our Python code also passes dates without timezone
Looking at `run_export.bat`, we pass `START=2024-06-12` and `END=2024-09-10`. These get passed to PI Web API as plain date strings. Since the PI server is in EST, PI interprets them the same way Craig's R code would — as EST midnight. So **our Python code and Craig's R code should be requesting the same time window**.

However, the Postman test used `T00:00:00Z` (UTC), which is different. The Postman test data is shifted 4 hours from what both Craig and our Python code would get.

### Finding 7: Numerical verification with Postman data
Using the 60 values from the Postman midnight-UTC hour (00:00Z to 00:59Z):
- Sum = ~152,400 GPM
- Average = ~2,540 GPM
- Converted to MGD: 2,540 × 0.00144 = **3.658 MGD**

Craig's first row (midnight EST): **2.184 MGD**
Our interpolated first row: **2.041 MGD**

The Postman average (3.658) doesn't match either, because the Postman test window (midnight UTC) covers a different set of minutes than midnight EST.

### Remaining investigation needed
The key question is: if both Craig's R code and our Python code pass `"2024-06-12"` as the start time (no timezone), and PI interprets both as EST midnight, then the raw 1-minute data should be identical. The difference must come from the client-side processing:

1. **`round_date("1h")` vs `replace(minute=0)`** — Craig rounds to nearest hour, we floor. This shifts values at the 30-minute boundary between adjacent hours.
2. **Unit conversion** — Craig's CSV is in MGD but we found no conversion in his R code. He may have a separate step, or the R piwebapi library may handle it differently than we think.
3. **The `1:00` value at hour boundaries** — Craig's R code includes the value at `01:00:00` in the 1AM group (via `round_date`), while our code includes it in the 1AM group too (via floor). But the value at `00:30:00` would round to 1AM in Craig's code but floor to 12AM in ours. This shifts ~30 values per hour boundary.

**Next step:** Run our Python interpolated method and manually verify the hourly average for the first hour against the raw 1-minute values, to confirm our averaging logic is correct. Then compare that specific hour's raw values against what Craig would have used.

---

## RESOLVED (2026-04-14)

### Root cause identified: floor vs round hour grouping
The value discrepancy was caused by `compute_hourly_averages` using `replace(minute=0)` (floor to hour) instead of rounding to the nearest hour like R's `round_date("1h")`.

After changing to round-to-nearest-hour (minutes 0-29 round down, minutes 30-59 round up), the interpolated method now matches Craig's CSV to 7-9 significant digits:

| Hour | Craig's | Our Interpolated (after fix) |
|------|---------|------------------------------|
| 12AM | 2.184343173 | 2.18434317343891 |
| 1AM | 1.872502524 | 1.87250252438592 |
| 2AM | 1.67814067 | 1.67814067029835 |
| 3AM | 1.380774392 | 1.38077439242347 |

The tiny trailing-digit differences are from R using Float32 precision vs Python using Float64.

### Why the PI summary method differs
The PI summary method (`/streams/{webId}/summary`) uses a trailing window (12:00-12:59 for midnight) while Craig's `round_date("1h")` creates a centered window (11:30-12:29 for midnight). These are fundamentally different averaging windows, which is why the PI summary values differ by 3-20%.

### Conclusion
- Use `--method interpolated` for Sliicer uploads (matches Craig exactly)
- The PI summary method is available but produces different values due to different hour boundary definitions
- Both PI Web API servers (prod and dev) return identical data — server choice doesn't matter
