@echo off
REM ============================================================
REM Export PI flow data to Sliicer CSV format
REM
REM Usage: run_export.bat
REM
REM Edit the variables below to change the tag, time range, etc.
REM
REM METHOD options:
REM   summary       - PI server-side hourly averages (default)
REM   interpolated  - Raw interpolated data at INTERVAL spacing,
REM                   then compute hourly averages client-side
REM
REM INTERVAL examples:
REM   1h  - hourly (default for summary)
REM   1m  - every minute (default for interpolated)
REM   15m - every 15 minutes
REM ============================================================

set TAG=wwl:south:wes8617b_realtmmetflo
set START=2024-06-12
set END=2024-09-10
set METHOD=summary
set INTERVAL=1h
set SUMMARY_TYPE=Average
set UNITS=gpm-to-mgd
set OUTPUT=

echo Running PI to Sliicer export...
echo Tag:          %TAG%
echo Start:        %START%
echo End:          %END%
echo Method:       %METHOD%
echo Interval:     %INTERVAL%
echo Summary Type: %SUMMARY_TYPE%
echo Units:        %UNITS%
echo Output:       %OUTPUT%
echo.

if "%OUTPUT%"=="" (
    ..\.venv\Scripts\python main.py "%TAG%" "%START%" "%END%" --method %METHOD% --interval %INTERVAL% --summary-type %SUMMARY_TYPE% --units %UNITS%
) else (
    ..\.venv\Scripts\python main.py "%TAG%" "%START%" "%END%" --method %METHOD% --interval %INTERVAL% --summary-type %SUMMARY_TYPE% --units %UNITS% --output "%OUTPUT%"
)

echo.
pause
