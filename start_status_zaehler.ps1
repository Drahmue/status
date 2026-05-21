# Zaehler Monitoring Service Starter - PowerShell Version
# Starts status_zaehler.py for continuous gas and electricity meter monitoring

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# Directory and logging configuration
$scriptDir = "\\HauServer\Dataserver\_Batchprozesse\status"
$LOGDIR = "$scriptDir\logs"
$LOGSTAMP = (Get-Date).ToString("yyyy-MM")
$LOGFILE = "$LOGDIR\status_zaehler_$LOGSTAMP.log"
$ERRORLOG = "$LOGDIR\status_zaehler_errors_$LOGSTAMP.log"

# Notification-Bibliothek laden
$notifyAvailable = $false
$notifyLib = Join-Path $scriptDir "Send-ErrorNotification.ps1"
if (Test-Path $notifyLib) {
    try {
        . $notifyLib
        $notifyAvailable = $true
    }
    catch { Write-Warning "FEHLER beim Laden der Notification-Bibliothek: $_" }
}

# Create logs directory if it doesn't exist
try {
    if (-not (Test-Path -Path $LOGDIR)) {
        New-Item -ItemType Directory -Path $LOGDIR -Force | Out-Null
    }
} catch {
    $LOGFILE = "C:\Temp\status_zaehler_emergency_$LOGSTAMP.log"
    $ERRORLOG = "C:\Temp\status_zaehler_emergency_errors_$LOGSTAMP.log"
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    "$timestamp CRITICAL: Could not create log directory at $LOGDIR. Error: $($_.Exception.Message)" | Out-File -FilePath $ERRORLOG -Append
}

# Log script start
try {
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    Add-Content -Path $LOGFILE -Value "$timestamp Starting Zaehler Monitoring Service"
    Add-Content -Path $LOGFILE -Value "$timestamp Running as user: $env:USERNAME"
} catch {
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    "$timestamp ERROR: Could not write to log file: $($_.Exception.Message)" | Out-File -FilePath $ERRORLOG -Append
}

# Navigate to script directory
try {
    Push-Location $scriptDir
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    Add-Content -Path $LOGFILE -Value "$timestamp Changed directory to: $scriptDir"
} catch {
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    $errorMsg = "$timestamp ERROR: Could not change to directory $scriptDir. Error: $($_.Exception.Message)"
    Add-Content -Path $LOGFILE -Value $errorMsg -ErrorAction SilentlyContinue
    "$errorMsg`nStack Trace: $($_.ScriptStackTrace)" | Out-File -FilePath $ERRORLOG -Append
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
    $pythonScript = "$scriptDir\status_zaehler.py"
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
    Add-Content -Path $LOGFILE -Value "$timestamp Starting Python script (status_zaehler.py)..."

    # status_zaehler.py runs continuously, so this will block until the script is stopped
    $pythonResult = & $venvPath -u $pythonScript 2>&1
    Add-Content -Path $LOGFILE -Value $pythonResult
    $RC = $LASTEXITCODE

    # Log completion (only reached if script exits)
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    if ($RC -eq 0) {
        Add-Content -Path $LOGFILE -Value "$timestamp Zaehler Monitoring script stopped normally"
    } else {
        Add-Content -Path $LOGFILE -Value "$timestamp ERROR: Zaehler Monitoring script failed with exit code $RC"
        Add-Content -Path $ERRORLOG -Value "$timestamp ERROR: Zaehler Monitoring script failed with exit code $RC"
        if ($notifyAvailable) {
            Send-ErrorNotification -ScriptName "start_status_zaehler (status_zaehler.py)" -ExitCode $RC `
                -ErrorMessage "Zaehler Monitoring script exited with code $RC" -LogFile $LOGFILE
        }
    }

    Add-Content -Path $LOGFILE -Value "$timestamp Zaehler Monitoring Service finished"

    # Clean up old log files (older than 120 days)
    $cutoffDate = (Get-Date).AddDays(-120)
    Get-ChildItem -Path $LOGDIR -Filter "status_zaehler_*.log" |
        Where-Object { $_.LastWriteTime -lt $cutoffDate } |
        Remove-Item -Force -ErrorAction SilentlyContinue

} catch {
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    $errorMsg = "$timestamp ERROR: $($_.Exception.Message)"
    Add-Content -Path $LOGFILE -Value $errorMsg -ErrorAction SilentlyContinue
    "$errorMsg`nStack Trace: $($_.ScriptStackTrace)" | Out-File -FilePath $ERRORLOG -Append
    $RC = 1
    if ($notifyAvailable) {
        Send-ErrorNotification -ScriptName "start_status_zaehler (status_zaehler.py)" -ExitCode $RC `
            -ErrorMessage $($_.Exception.Message) -LogFile $LOGFILE
    }
}

Pop-Location
exit $RC
