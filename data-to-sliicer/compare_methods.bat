@echo off
REM ============================================================
REM Compare PI data retrieval methods side by side
REM
REM Produces two CSV files for the same tag and time range:
REM   {SITE_ID}_interpolated.csv  - 1m interpolated + client-side hourly avg (Craig's method)
REM   {SITE_ID}_pi-summary.csv   - PI server-side hourly average
REM
REM The SITE_ID is derived automatically from the TAG name.
REM Compare both against Craig's examples in the examples\ folder.
REM ============================================================

set TAG=wwl:south:wes8617b_realtmmetflo
set START=2024-06-12
set END=2024-09-10
set UNITS=gpm-to-mgd

echo ============================================================
echo  Method Comparison: %TAG%
echo  Range: %START% to %END%
echo  Units: %UNITS%
echo ============================================================
echo.

echo [1/2] Running INTERPOLATED method (1m data + client-side hourly avg)...
..\.venv\Scripts\python main.py "%TAG%" "%START%" "%END%" --method interpolated --interval 1m --units %UNITS% --output-suffix _interpolated
echo.

echo [2/2] Running PI SUMMARY method (server-side hourly average)...
..\.venv\Scripts\python main.py "%TAG%" "%START%" "%END%" --method summary --interval 1h --summary-type Average --units %UNITS% --output-suffix _pi-summary
echo.

echo ============================================================
echo  Done. Check the output CSV files.
echo ============================================================
echo.
pause
