@echo off
setlocal enabledelayedexpansion
echo Testing input...
set "VAR="
set /p "VAR=Enter y: "
echo You entered: !VAR!
if "!VAR!"=="" (
    echo Empty, setting to Y
    set "VAR=Y"
)
if /i not "!VAR!"=="n" (
    echo Proceeding...
) else (
    echo Skipping
)
pause
