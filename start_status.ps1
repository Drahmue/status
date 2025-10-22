# Stock Monitoring Service Starter - PowerShell Version
# Converted from start_status.bat to handle UNC paths properly
# Version with network wait logic (3-5 minute timeout)

# Set error action preference and encoding
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# Early error logging setup (before main script execution)
$scriptDir = "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status"
$LOGDIR = "$scriptDir\logs"
$LOGSTAMP = (Get-Date).ToString("yyyy-MM")
$LOGFILE = "$LOGDIR\status_$LOGSTAMP.log"
$ERRORLOG = "$LOGDIR\status_errors_$LOGSTAMP.log"

# Network file paths to check
$NETWORK_PATH = "\\WIN-H7BKO5H0RMC\Dataserver"
$REQUIRED_FILE1 = "\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx"
$REQUIRED_FILE2 = "\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\bookings.xlsx"

# Network wait configuration: 3-5 minutes (60 attempts * 5 seconds = 5 minutes)
$MAX_NETWORK_WAIT = 60
$WAIT_INTERVAL_SECONDS = 5

# Function to wait for network resources
function Wait-ForNetworkResources {
    param (
        [string]$LogFile,
        [string]$ErrorLog
    )

    $attempt = 0

    while ($attempt -lt $MAX_NETWORK_WAIT) {
        $attempt++

        # Check if network share root exists
        if (-not (Test-Path -Path $NETWORK_PATH)) {
            $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
            Add-Content -Path $LogFile -Value "$timestamp Waiting for network share to be available (attempt $attempt/$MAX_NETWORK_WAIT)..." -ErrorAction SilentlyContinue
            Start-Sleep -Seconds $WAIT_INTERVAL_SECONDS
            continue
        }

        # Check if required file 1 exists
        if (-not (Test-Path -Path $REQUIRED_FILE1)) {
            $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
            Add-Content -Path $LogFile -Value "$timestamp Waiting for required file Instrumente.xlsx (attempt $attempt/$MAX_NETWORK_WAIT)..." -ErrorAction SilentlyContinue
            Start-Sleep -Seconds $WAIT_INTERVAL_SECONDS
            continue
        }

        # Check if required file 2 exists
        if (-not (Test-Path -Path $REQUIRED_FILE2)) {
            $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
            Add-Content -Path $LogFile -Value "$timestamp Waiting for required file bookings.xlsx (attempt $attempt/$MAX_NETWORK_WAIT)..." -ErrorAction SilentlyContinue
            Start-Sleep -Seconds $WAIT_INTERVAL_SECONDS
            continue
        }

        # All resources are available
        $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
        Add-Content -Path $LogFile -Value "$timestamp Network share $NETWORK_PATH is available" -ErrorAction SilentlyContinue
        Add-Content -Path $LogFile -Value "$timestamp All required files are accessible" -ErrorAction SilentlyContinue
        return $true
    }

    # Timeout reached
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    $errorMsg = "$timestamp ERROR: Network resources not available after $MAX_NETWORK_WAIT attempts"
    Add-Content -Path $LogFile -Value $errorMsg -ErrorAction SilentlyContinue
    Add-Content -Path $ErrorLog -Value $errorMsg -ErrorAction SilentlyContinue
    return $false
}

# Create logs directory if it doesn't exist
try {
    if (-not (Test-Path -Path $LOGDIR)) {
        New-Item -ItemType Directory -Path $LOGDIR -Force | Out-Null
    }
} catch {
    # If we can't even create the log directory, write to a fallback location
    $LOGFILE = "C:\Temp\status_emergency_$LOGSTAMP.log"
    $ERRORLOG = "C:\Temp\status_emergency_errors_$LOGSTAMP.log"
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    "$timestamp CRITICAL: Could not create log directory at $LOGDIR. Error: $($_.Exception.Message)" | Out-File -FilePath $ERRORLOG -Append
}

# Log script start
try {
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    Add-Content -Path $LOGFILE -Value "$timestamp Starting Stock Monitoring Service"
    Add-Content -Path $LOGFILE -Value "$timestamp Running as user: $env:USERNAME"
} catch {
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    "$timestamp ERROR: Could not write to log file: $($_.Exception.Message)" | Out-File -FilePath $ERRORLOG -Append
}

# Wait for network resources to be available
$timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
Add-Content -Path $LOGFILE -Value "$timestamp Checking network resource availability..." -ErrorAction SilentlyContinue

if (-not (Wait-ForNetworkResources -LogFile $LOGFILE -ErrorLog $ERRORLOG)) {
    exit 1
}

# Navigate to script directory
try {
    Push-Location $scriptDir
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    Add-Content -Path $LOGFILE -Value "$timestamp Changed directory to: $scriptDir"
} catch {
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    "$timestamp ERROR: Could not change to directory $scriptDir. Error: $($_.Exception.Message)" | Out-File -FilePath $ERRORLOG -Append
    Add-Content -Path $LOGFILE -Value "$timestamp ERROR: Could not change to directory $scriptDir"
    exit 1
}

try {
    # Check if virtual environment exists
    $venvPath = "$scriptDir\.venv\Scripts\python.exe"
    if (-not (Test-Path -Path $venvPath)) {
        $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
        $errorMsg = "$timestamp ERROR: Virtual environment not found at $venvPath"
        Add-Content -Path $LOGFILE -Value $errorMsg
        Add-Content -Path $ERRORLOG -Value $errorMsg
        Pop-Location
        exit 1
    }

    # Check if Python script exists
    $pythonScript = "$scriptDir\status.py"
    if (-not (Test-Path -Path $pythonScript)) {
        $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
        $errorMsg = "$timestamp ERROR: Python script not found at $pythonScript"
        Add-Content -Path $LOGFILE -Value $errorMsg
        Add-Content -Path $ERRORLOG -Value $errorMsg
        Pop-Location
        exit 1
    }

    # Run the Python script
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    Add-Content -Path $LOGFILE -Value "$timestamp Starting Python script..."

    $pythonResult = & $venvPath -u $pythonScript 2>&1
    Add-Content -Path $LOGFILE -Value $pythonResult
    $RC = $LASTEXITCODE

    # Log completion
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    if ($RC -eq 0) {
        Add-Content -Path $LOGFILE -Value "$timestamp Python script completed successfully"
    } else {
        Add-Content -Path $LOGFILE -Value "$timestamp ERROR: Python script failed with exit code $RC"
        Add-Content -Path $ERRORLOG -Value "$timestamp ERROR: Python script failed with exit code $RC"
    }

    Add-Content -Path $LOGFILE -Value "$timestamp Stock Monitoring Service finished"

    # Clean up old log files (older than 120 days)
    $cutoffDate = (Get-Date).AddDays(-120)
    Get-ChildItem -Path $LOGDIR -Filter "status_*.log" |
        Where-Object { $_.LastWriteTime -lt $cutoffDate } |
        Remove-Item -Force -ErrorAction SilentlyContinue

} catch {
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    $errorMsg = "$timestamp ERROR: $($_.Exception.Message)"
    Add-Content -Path $LOGFILE -Value $errorMsg -ErrorAction SilentlyContinue
    "$errorMsg`nStack Trace: $($_.ScriptStackTrace)" | Out-File -FilePath $ERRORLOG -Append
    $RC = 1
}

# Exit with the return code
Pop-Location
exit $RC
