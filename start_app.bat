@echo off
REM Flask Web Application Starter
REM Task 1 - Start app.py with system start

cd /d "D:\Dataserver\_Batchprozesse\status"
python app.py

REM Keep window open if there's an error
if errorlevel 1 pause