@echo off
REM DSL Speedtest Monitoring Service Starter
REM Task 3 - Start status_dsl.py

cd /d "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status"
call .venv\Scripts\activate
python status_dsl.py

REM Keep window open if there's an error
if errorlevel 1 pause