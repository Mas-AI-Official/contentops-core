@echo off
title Content OPS AI - Cleanup (manual)
REM Use this only when you want to stop all Python/Node processes. launch.bat does NOT kill processes.
echo Killing Python processes...
taskkill /F /IM python.exe /T
echo Killing Node processes...
taskkill /F /IM node.exe /T
echo.
echo Cleanup complete.
pause
