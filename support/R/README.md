
# Step 1: Build PI Tags from GIS

## 1.1) Get list of tags from GIS

Downloads pump station features from GIS, filters to in-service lift stations with a CMMS asset ID.

```r
get_ls_from_gis <- function() {
    load_gis_ps() %>%
    st_drop_geometry() %>%                  # remove x,y
    filter(FAC_STATE == "INS") %>%          # In-Service Only
    filter(!is.na(CMMS_ASSET_ID)) %>%       # Has CMMS_ASSET_ID
    filter(SUBTYPE == 1) %>%                # is a Liftstation
    dplyr::select(STREET_NAME, STREET_NUMBER, CMMS_ASSET_ID, PI_TAG)
}
```

## 1.2) Classify and validate tags

`classify_tags()` splits tags into categories and checks each against the PI Web API.
`print_tag_summary()` displays the results as a tree.

```
                   levelName matches     pct
1 Pump Stations                 1696
2  |--Missing Data (NA)           17    (1%)
3  |--Missing Underscore        1674
4  |   |--Bad Tag                 20  (1.2%)
5  |   °--Valid Otherwise       1654 (97.5%)
6  |--Correct Format               0
7  |   |--Bad Tag                  0    (0%)
8  |   °--OK                       0    (0%)
9  °--No SCADA                     5  (0.3%)
```

## 1.3) Try to guess correct tag names

For tags that are missing or invalid, `guess_tag_name()` builds candidate tag names
from the street name and address, then checks each against the PI Web API.

Candidate format: `{site}:{grid}:{first 3 chars of street}{address}_{measurement}`.

- {site} = wwl, for liftstations
- {grid} = north, east, south, west, nassau, stjohns
- {first 3 chars of street}{address}, see `guess.R`
- {measurement} = used `_P1RUN` because it is common to all liftstations.

Suffixes tried:
- `""` (standard station)
- `"B"` (booster pump)
- `"-1"` (new station placeholder)

Stops at the first valid match per asset to minimize API calls.

## 1.4) Export

The corrected tags are joined back with the original GIS data and exported
to `data/pi_tag_master_list.csv`. Duplicate CMMS_ASSET_IDs and PI_TAGs
are printed as warnings for manual review.

---

# Step 2: Check Pump Tags and Build AF Import Data

## 2.1) Check all pump tags

`check_all_pump_tags()` generates 16 tag candidates per station (4 pumps x 4 measurements:
RUN, FRQ, RSPD, CSPD) and validates each against the PI Web API.

## 2.2) Identify multi-pump and VFD stations

`get_scada_history()` pulls 7 days of SCADA history for valid tags (excluding P1RUN/P2RUN).

`check_multiple_pumps_or_vfd_control()` analyzes the history to identify stations
with more than 2 pumps or VFD speed control. Stations with >2 pumps are excluded
from the standard template flow.

## 2.3) Check lead setpoint tags

For remaining stations, checks if a `_WLLEADSP` tag exists. Stations with
a lead setpoint get the `_cte_leadsp` template; those without get `_cte_lead`.

## 2.4) Join reference data and export

Joins with plant basin assignments (`get_ls_by_plant()`) and wetwell diameter
data (`get_dia_by_ls()`). These are currently loaded from RData files but are
placeholder functions intended to be replaced with computed lookups.

Exports to `data/pi_af_import.csv` with columns:
BASIN, STATION_NAME, CMMS_ASSET_ID, PI_TAG, Dia, TEMPLATE

---

# Step 3: Format for PI AF CSV Loader

`export_af()` reads `data/pi_af_import.csv` and builds the hierarchical
CSV structure required by the PI Asset Framework bulk import tool.

Output hierarchy:
```
WASTEWATER
  └── EST FLOW
        └── {BASIN}
              └── {STATION_NAME}  (Template: _Liftstation)
                    ├── CMMS Asset ID  (Attribute)
                    ├── PI Tag         (Attribute)
                    ├── Wetwell Area   (Attribute)
                    ├── cte            (Element, template varies)
                    └── hrt            (Element, template: _hrt)
```

Exports to `out/pi_af_loader.csv`.
