@echo off
REM Stock Monitoring Service Starter
REM Task 2 - Start status.py

cd /d "D:\Dataserver\_Batchprozesse\status"
call .venv\Scripts\activate
python status.py

REM Keep window open if there's an error
if errorlevel 1 pause