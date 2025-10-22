@echo off
REM Stock Monitoring Service Starter
REM Task 2 - Start status.py
REM Version for Service Account with enhanced logging and error handling

setlocal EnableDelayedExpansion

REM Set variables
set SCRIPT_DIR=\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status
set LOG_FILE=%SCRIPT_DIR%\task_scheduler.log
set VENV_PATH=%SCRIPT_DIR%\.venv\Scripts
set PYTHON_SCRIPT=%SCRIPT_DIR%\status.py

REM Create log entry with timestamp
echo [%DATE% %TIME%] Starting Stock Monitoring Service >> "%LOG_FILE%"
echo [%DATE% %TIME%] Running as user: %USERNAME% >> "%LOG_FILE%"

REM Change to script directory
cd /d "%SCRIPT_DIR%"
if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to change to directory %SCRIPT_DIR% >> "%LOG_FILE%"
    exit /b 1
)

REM Check if virtual environment exists
if not exist "%VENV_PATH%\activate.bat" (
    echo [%DATE% %TIME%] ERROR: Virtual environment not found at %VENV_PATH% >> "%LOG_FILE%"
    exit /b 1
)

REM Check if Python script exists
if not exist "%PYTHON_SCRIPT%" (
    echo [%DATE% %TIME%] ERROR: Python script not found at %PYTHON_SCRIPT% >> "%LOG_FILE%"
    exit /b 1
)

REM Wait for network share and required files to be available
set NETWORK_PATH=\\WIN-H7BKO5H0RMC\Dataserver
set REQUIRED_FILE1=\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx
set REQUIRED_FILE2=\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\bookings.xlsx
set MAX_NETWORK_WAIT=120
set NETWORK_WAIT_COUNT=0

:WAIT_FOR_NETWORK
REM Check if network share root exists
if not exist "%NETWORK_PATH%\" (
    set /a NETWORK_WAIT_COUNT+=1
    if %NETWORK_WAIT_COUNT% gtr %MAX_NETWORK_WAIT% (
        echo [%DATE% %TIME%] ERROR: Network share %NETWORK_PATH% not available after %MAX_NETWORK_WAIT% attempts >> "%LOG_FILE%"
        exit /b 1
    )
    echo [%DATE% %TIME%] Waiting for network share to be available (attempt %NETWORK_WAIT_COUNT%/%MAX_NETWORK_WAIT%)... >> "%LOG_FILE%"
    timeout /t 5 /nobreak > nul
    goto WAIT_FOR_NETWORK
)

REM Check if required files exist
if not exist "%REQUIRED_FILE1%" (
    set /a NETWORK_WAIT_COUNT+=1
    if %NETWORK_WAIT_COUNT% gtr %MAX_NETWORK_WAIT% (
        echo [%DATE% %TIME%] ERROR: Required file %REQUIRED_FILE1% not available after %MAX_NETWORK_WAIT% attempts >> "%LOG_FILE%"
        exit /b 1
    )
    echo [%DATE% %TIME%] Waiting for required files to be available (attempt %NETWORK_WAIT_COUNT%/%MAX_NETWORK_WAIT%)... >> "%LOG_FILE%"
    timeout /t 5 /nobreak > nul
    goto WAIT_FOR_NETWORK
)

if not exist "%REQUIRED_FILE2%" (
    set /a NETWORK_WAIT_COUNT+=1
    if %NETWORK_WAIT_COUNT% gtr %MAX_NETWORK_WAIT% (
        echo [%DATE% %TIME%] ERROR: Required file %REQUIRED_FILE2% not available after %MAX_NETWORK_WAIT% attempts >> "%LOG_FILE%"
        exit /b 1
    )
    echo [%DATE% %TIME%] Waiting for required files to be available (attempt %NETWORK_WAIT_COUNT%/%MAX_NETWORK_WAIT%)... >> "%LOG_FILE%"
    timeout /t 5 /nobreak > nul
    goto WAIT_FOR_NETWORK
)

echo [%DATE% %TIME%] Network share %NETWORK_PATH% is available >> "%LOG_FILE%"
echo [%DATE% %TIME%] All required files are accessible >> "%LOG_FILE%"

REM Activate virtual environment
echo [%DATE% %TIME%] Activating virtual environment... >> "%LOG_FILE%"
call "%VENV_PATH%\activate.bat"
if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to activate virtual environment >> "%LOG_FILE%"
    exit /b 1
)

REM Run the Python script
echo [%DATE% %TIME%] Starting Python script... >> "%LOG_FILE%"
python "%PYTHON_SCRIPT%"
set PYTHON_EXIT_CODE=%errorlevel%

REM Log the result
if %PYTHON_EXIT_CODE% equ 0 (
    echo [%DATE% %TIME%] Python script completed successfully >> "%LOG_FILE%"
) else (
    echo [%DATE% %TIME%] ERROR: Python script failed with exit code %PYTHON_EXIT_CODE% >> "%LOG_FILE%"
)

echo [%DATE% %TIME%] Stock Monitoring Service finished >> "%LOG_FILE%"
exit /b %PYTHON_EXIT_CODE%