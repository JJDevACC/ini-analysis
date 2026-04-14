@echo off
REM ============================================================
REM Compare PI data retrieval methods side by side
REM
REM Produces two CSV files for the same tag and time range:
REM   {SITE_ID}_interpolated.csv  - 1m interpolated + client-side hourly avg (Craig's method)
REM   {SITE_ID}_pi-summary.csv   - PI server-side hourly average
REM
REM Compare both against Craig's example at examples\WES8617.csv
REM ============================================================

set TAG=wwl:south:wes8617b_realtmmetflo
set START=2024-06-12
set END=2024-09-10
set UNITS=gpm-to-mgd
set SITE_ID=WES8617

echo ============================================================
echo  Method Comparison: %TAG%
echo  Range: %START% to %END%
echo  Units: %UNITS%
echo ============================================================
echo.

echo [1/2] Running INTERPOLATED method (1m data + client-side hourly avg)...
echo       Output: %SITE_ID%_interpolated.csv
..\.venv\Scripts\python main.py "%TAG%" "%START%" "%END%" --method interpolated --interval 1m --units %UNITS% --output %SITE_ID%_interpolated.csv
echo.

echo [2/2] Running PI SUMMARY method (server-side hourly average)...
echo       Output: %SITE_ID%_pi-summary.csv
..\.venv\Scripts\python main.py "%TAG%" "%START%" "%END%" --method summary --interval 1h --summary-type Average --units %UNITS% --output %SITE_ID%_pi-summary.csv
echo.

echo ============================================================
echo  Done. Compare these files:
echo    %SITE_ID%_interpolated.csv   (Craig's method)
echo    %SITE_ID%_pi-summary.csv     (PI server-side)
echo    examples\WES8617.csv         (Craig's original)
echo ============================================================
echo.
pause
