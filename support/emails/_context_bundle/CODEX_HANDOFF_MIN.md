# Codex Migration Handoff (Token-Light)

## 1) Objective
Migrate the R pipeline that prepares PI AF loader CSVs into Python with behavior parity first, then automate execution (eventually AWS).

## 2) Scope Used
Only analyzed files under `support/`:
- `support/R/*`
- `support/emails/_context_bundle/*`
- extracted email artifacts under `support/emails/*.extracted/*`
- `support/pi_tag_master_list.csv`
- `support/pi_af_import.csv`
- `support/pi_af_loader.csv`
- `support/package_structure.html`

## 3) Confirmed Current Pipeline (R)
Entry points (run order):
1. `validate_gis()` -> outputs `pi_tag_master_list.csv`
2. `validate_csv()` -> manual QA pass
3. `build_af()` -> outputs `pi_af_import.csv`
4. `export_af()` -> outputs `pi_af_loader.csv`

Primary files:
- `support/R/R/pipeline.R`
- `support/R/R/io.R`
- `support/R/R/check_tags.R`
- `support/R/R/guess.R`
- `support/R/R/validate.R`
- `support/R/R/af_format.R`

## 4) Artifact Reality (provided outputs)
- `pi_tag_master_list.csv`: 1693 rows
- `pi_af_import.csv`: 1589 rows
- `pi_af_loader.csv`: 9548 rows
- Loader row math checks: `1 root + 13 basin rows + 6 * 1589 station rows = 9548`.

## 5) What Is Implemented vs Missing
Implemented:
- Tag classification/cleanup/guessing logic
- Pump tag variant checks
- VFD / multi-pump detection heuristic
- AF CSV hierarchy formatter

Missing/External:
- Actual PI Web API environment config (base URL/auth/network)
- Actual GIS API contract (layer/query details)
- ADS Prism API implementation
- End-to-end automation/orchestration

## 6) Critical Gaps (block full Python parity)
1. PI connectivity details unknown.
2. GIS source contract + ArcPy/service query details unknown.
3. Business rule conflict: docs/email wording vs code behavior on VFD and pump-count exclusions.
4. Manual review step is currently required (`validate_csv` workflow).
5. Canonical source for `ls_by_plant`/wetwell derivation is not fully productized.

## 7) Specific `.RData` Context from Craig Email
Craig clarified:
- `ls_by_plant` is produced by GIS spatial join: CURRENT service area polygon -> lift station plant assignment.
- `dia_by_ls` combines AF wetwell area + GIS wetwell diameter (from EAM), then chooses "best" value with comparison logic.
- He notes this should be improved with ArcPy.

Related code screenshots in email align with `support/R/R/io.R` logic:
- `get_ls_by_plant()`
- `get_dia_by_ls()`

## 8) Recommended Next Build Slice (local, this week)
Implement Python Step 3 parity first:
- Input: `support/pi_af_import.csv`
- Output: generated `pi_af_loader.csv`
- No external APIs required
- Fast parity win and deterministic tests

## 9) Stakeholder Questions to Resolve Before Full Migration
- PI: URL/auth/timezone/sampling/quality semantics?
- GIS: authoritative source and reproducible query/join definitions?
- Rules: exact exclusion policy for VFD and pump count?
- Ops: run cadence, failure handling, approvals, and ownership?
- ADS: exact endpoint/auth/payload for direct insert?

## 10) Fast Start Prompt for Next Codex Session
"Read `support/emails/_context_bundle/CODEX_HANDOFF_MIN.md` first. Then use `support/R/R/*.R` to implement Python Step 3 (`pi_af_import.csv` -> `pi_af_loader.csv`) with parity tests against `support/pi_af_loader.csv`. Flag any behavior mismatch as rules-vs-code ambiguity, not silent assumptions."
