@echo off
title Content OPS AI - Cleanup
echo Killing Python processes...
taskkill /F /IM python.exe /T
echo Killing Node processes...
taskkill /F /IM node.exe /T
echo.
echo Cleanup complete.
pause
