@echo off
REM ============================================================
REM Test PI Web API connection and data retrieval
REM
REM Usage: test_connection.bat
REM
REM Edit the variables below to change the tag, time range, etc.
REM
REM METHOD options:
REM   summary       - PI server-side hourly averages (default)
REM   interpolated  - Raw interpolated data at INTERVAL spacing
REM
REM INTERVAL examples:
REM   1h  - hourly (default for summary)
REM   1m  - every minute (default for interpolated)
REM   15m - every 15 minutes
REM ============================================================

set TAG=wwl:south:wes8617b_realtmmetflo
set START=*-5d
set END=*
set METHOD=summary
set INTERVAL=1h
set SUMMARY_TYPE=Average

echo Running PI Web API connection test...
echo Tag:          %TAG%
echo Start:        %START%
echo End:          %END%
echo Method:       %METHOD%
echo Interval:     %INTERVAL%
echo Summary Type: %SUMMARY_TYPE%
echo.

..\.venv\Scripts\python test_connection.py "%TAG%" "%START%" "%END%" --method %METHOD% --interval %INTERVAL% --summary-type %SUMMARY_TYPE%

echo.
pause
