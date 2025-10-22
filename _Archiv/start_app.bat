@echo off
REM Flask Web Application Starter
REM Task 1 - Start app.py with system start

cd /d "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status"
call .venv\Scripts\activate
python app.py

REM Keep window open if there's an error
if errorlevel 1 pause