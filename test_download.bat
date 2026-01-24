@echo off
setlocal enabledelayedexpansion

set ROOT=D:\Ideas\content_factory
set VENV_PYTHON=%ROOT%\venv\Scripts\python.exe

echo Testing download script execution...
echo.

if exist "%ROOT%\download_ltx_simple.py" (
    echo Found download_ltx_simple.py
    echo Executing...
    call "%VENV_PYTHON%" "%ROOT%\download_ltx_simple.py"
    set TEST_EXIT=!errorlevel!
    echo.
    echo Exit code: !TEST_EXIT!
) else (
    echo download_ltx_simple.py not found
)

echo.
echo Test complete.
pause