@echo off
cd /d "%~dp0"
set SMARTFLOW_MODE=dev
start "" wscript.exe "%~dp0RUN_DEV.vbs"
