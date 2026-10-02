@echo off
cd /d "%~dp0"
set SMARTFLOW_MODE=dev
".venv\Scripts\python.exe" -m smartflow.cli desktop
if errorlevel 1 pause
