# Windows Server Deployment Guide

**Version:** 2.0 (Updated 2025-10-22)
**Status:** PowerShell-based deployment with centralized logging

This document describes how to deploy the Status monitoring system on a Windows Server using Task Scheduler to run services automatically on system startup.

## Overview

The deployment consists of 3 automated services running as PowerShell scripts:
1. **Flask Web App** (`start_app.ps1` → `app.py`) - Web dashboard for monitoring
2. **Stock Monitor** (`start_status.ps1` → `status.py`) - Stock price monitoring and portfolio tracking
3. **DSL Speedtest** (`start_status_dsl.ps1` → `status_dsl.py`) - Internet speed monitoring and data collection

### Key Features

- ✅ **PowerShell-based** - Native UNC path support, robust error handling
- ✅ **Centralized Logging** - All logs in `logs\` directory with monthly rotation
- ✅ **Automatic Log Cleanup** - Logs older than 120 days are automatically deleted
- ✅ **Separate Error Logs** - Quick error diagnosis with dedicated error log files
- ✅ **UTF-8 Encoding** - Full support for German Umlaute (ä, ö, ü, ß)
- ✅ **Network Resilience** - Automatic wait for network shares on startup
- ✅ **Service Account Support** - Runs under dedicated service account

## Prerequisites

- Windows Server with Administrator access
- Python 3.8+ installed with virtual environment
- Git repository cloned to `\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status`
- Service account configured on the server (e.g., "Service")
- Service account password available for task registration
- Required Python packages installed in virtual environment

## Step 1: Repository Setup

### 1.1 Clone Repository on Server

```cmd
cd D:\Dataserver\_Batchprozesse
git clone [repository-url] status
cd status
```

### 1.2 Create Virtual Environment

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 1.3 Pull Latest Updates

```cmd
git pull origin main
```

### 1.4 Verify PowerShell Scripts

Ensure these PowerShell scripts are present:
- `start_app.ps1` - Flask Web Application starter
- `start_status.ps1` - Stock Monitoring Service starter
- `start_status_dsl.ps1` - DSL Speedtest Monitoring starter

### 1.5 Create Required Directories

```powershell
# Create logs directory if not exists
New-Item -Path "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs" -ItemType Directory -Force

# Create static directory if not exists
New-Item -Path "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\static" -ItemType Directory -Force
```

## Step 2: Service Account Permissions

### 2.1 Grant Folder Permissions

1. Navigate to `\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status`
2. Right-click → **Properties** → **Security** tab
3. Click **"Edit..."** → **"Add..."**
4. Enter `Service` → **"Check Names"** → **OK**
5. Select `Service` user → Grant permissions:
   - ☑️ **Full control** (recommended)
   - Or minimum: Read & execute, Write, Modify
6. Click **"Advanced"** → Check **"Replace all child object permissions"**
7. **Apply** to all subfolders and files

**Important directories requiring write access:**
- `logs\` - For log files
- `static\` - For JSON output files
- Root directory - For Parquet data files

### 2.2 Grant "Log on as a Service" Right

1. Press `Win + R`, type `secpol.msc`, press **Enter**
2. Navigate: **Security Settings** → **Local Policies** → **User Rights Assignment**
3. Double-click **"Log on as a service"**
4. Click **"Add User or Group..."** → Enter `Service` → **OK**
5. **Apply** changes

### 2.3 Network Share Access

Ensure `Service` account has access to:
- `\\WIN-H7BKO5H0RMC\Dataserver\` (network share root)
- `\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx`
- `\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\bookings.xlsx`

**Test network access:**
```powershell
# Run as Service account
Test-Path "\\WIN-H7BKO5H0RMC\Dataserver\Dummy\Finance_Input\Instrumente.xlsx"
# Should return: True
```

### 2.4 PowerShell Execution Policy

Ensure PowerShell can execute scripts from UNC paths:
```powershell
# Check current policy
Get-ExecutionPolicy

# If needed, set to allow scripts (as Administrator)
Set-ExecutionPolicy RemoteSigned -Scope LocalMachine
```

**Note:** Tasks use `-ExecutionPolicy Bypass` parameter, so this is not strictly required.

## Step 3: Task Scheduler Configuration

### 3.1 Open Task Scheduler

1. Press `Win + R`, type `taskschd.msc`, press **Enter**
2. Run as **Administrator**
3. Navigate to **"Task Scheduler Library"**
4. Create folder: Right-click → **"New Folder..."** → Name: `AHSkripts`
5. Navigate into the `AHSkripts` folder

### 3.2 Task 1: Flask Web Application

**General Tab:**
- **Name:** `Status Web App`
- **Description:** `Flask web application for stock monitoring dashboard (PowerShell)`
- Click **"Change User or Group..."**
  - Enter: `Service`
  - **OK**
- ☑️ **Run whether user is logged on or not**
- ☑️ **Run with highest privileges**
- **Configure for:** Windows Server (your version)

**Triggers Tab:**
- Click **"New..."**
- **Begin the task:** At startup
- **Delay task for:** (no delay)
- ☑️ **Enabled**
- **OK**

**Actions Tab:**
- Click **"New..."**
- **Action:** Start a program
- **Program/script:** `powershell.exe`
- **Add arguments:**
  ```
  -ExecutionPolicy Bypass -File "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\start_app.ps1"
  ```
- **Start in:** (leave empty - PowerShell handles UNC paths)
- **OK**

**Conditions Tab:**
- ☐ **Uncheck:** "Start the task only if the computer is on AC power"
- ☑️ **Check:** "Wake the computer to run this task" (optional)

**Settings Tab:**
- ☑️ Allow task to be run on demand
- ☑️ Run task as soon as possible after a scheduled start is missed
- ☐ Stop the task if it runs longer than: (uncheck - runs continuously)
- **If the running task does not end when requested, force it to stop**
- **If the task is already running:** Do not start a new instance

**Save Task:**
- Click **OK**
- Enter password for `Service` account when prompted
- **OK**

### 3.3 Task 2: Stock Monitoring Service

**General Tab:**
- **Name:** `Stock Monitoring Service`
- **Description:** `Stock price monitoring and portfolio tracking (PowerShell with network wait)`
- **User account:** `Service`
- ☑️ **Run whether user is logged on or not**
- ☑️ **Run with highest privileges**

**Triggers Tab:**
- **Begin the task:** At startup
- **Delay task for:** `2 minutes` (wait for network initialization)
- ☑️ **Enabled**

**Actions Tab:**
- **Program/script:** `powershell.exe`
- **Add arguments:**
  ```
  -ExecutionPolicy Bypass -File "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\start_status.ps1"
  ```
- **Start in:** (leave empty)

**Conditions & Settings:** Same as Task 1

**Save with Service account password**

**Special Features:**
- Automatic network share availability check (waits up to 5 minutes)
- Verifies Excel files are accessible before starting
- Detailed logging of network wait process

### 3.4 Task 3: DSL Speedtest Monitoring

**General Tab:**
- **Name:** `DSL Speedtest Monitoring`
- **Description:** `DSL speedtest monitoring and data collection (PowerShell)`
- **User account:** `Service`
- ☑️ **Run whether user is logged on or not**
- ☑️ **Run with highest privileges**

**Triggers Tab:**
- **Begin the task:** At startup
- **Delay task for:** `3 minutes` (wait for other services)
- ☑️ **Enabled**

**Actions Tab:**
- **Program/script:** `powershell.exe`
- **Add arguments:**
  ```
  -ExecutionPolicy Bypass -File "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\start_status_dsl.ps1"
  ```
- **Start in:** (leave empty)

**Conditions & Settings:** Same as Task 1

**Save with Service account password**

### 3.5 Verify Task Configuration

After creating all tasks:

```powershell
# List tasks in AHSkripts folder
Get-ScheduledTask -TaskPath "\AHSkripts\" | Select-Object TaskName, State | Format-Table

# Expected output:
# TaskName                   State
# --------                   -----
# Status Web App             Ready
# Stock Monitoring Service   Ready
# DSL Speedtest Monitoring   Ready
```

## Step 4: Windows Firewall Configuration

### Open Port 5000 for Flask Application

1. Open **Windows Defender Firewall with Advanced Security**
2. Click **"Inbound Rules"** → **"New Rule..."**
3. **Rule Type:** Port
4. **Protocol:** TCP, **Specific local ports:** `5000`
5. **Action:** Allow the connection
6. **Profile:** Apply to Domain, Private, and Public
7. **Name:** `Flask Status Dashboard`
8. **Description:** `Allows access to stock monitoring web dashboard on port 5000`

## Step 5: Testing and Verification

### 5.1 Automated Service-User Testing (Recommended)

**Important:** Before deploying to production, test all scripts with the Service account using PowerShell automation.

**Test Script Location:**
```
_Archiv\test_as_service_with_password.ps1
```

**Running the Automated Tests:**

1. **Open PowerShell as Administrator:**
   - Press `Win + X` → **"Windows PowerShell (Admin)"**

2. **Navigate to the script directory:**
   ```powershell
   cd "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status"
   ```

3. **Run the test script:**
   ```powershell
   .\_Archiv\test_as_service_with_password.ps1
   ```

4. **Enter Service account password when prompted:**
   - A credential dialog will appear
   - Username: `Service` (pre-filled)
   - Enter the password
   - Click **OK**

**What the Test Does:**

The automated test script performs the following:
1. **Creates temporary test tasks** with Service account credentials
2. **Runs each task** for 15 seconds to verify startup
3. **Checks log files** are created and contain "Running as user: Service"
4. **Verifies no error logs** are created
5. **Stops and removes** test tasks automatically
6. **Generates test report** in `logs\service_test_YYYY-MM-DD_HHMMSS.log`

**Expected Output:**

```
========================================
  TESTING COMPLETE
========================================
Passed: 3 / Failed: 0
Log file: logs\service_test_2025-10-22_100309.log
```

**Test Results Interpretation:**

- **3/3 PASSED** - All services work correctly with Service account ✓
- **Any FAILED** - Check the test log file for detailed error messages

**Reviewing Test Logs:**

```powershell
# View latest test log
$latestTestLog = Get-ChildItem "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs\service_test_*.log" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

Get-Content $latestTestLog.FullName | Select-String "PASSED|FAILED|ERROR"
```

**Troubleshooting Test Failures:**

If tests fail:
1. Review the full test log: `logs\service_test_*.log`
2. Check Service account permissions (see Section 2.1)
3. Verify Service account password is correct
4. Check "Log on as a service" right is granted
5. Ensure network shares are accessible

**Manual Testing Alternative:**

If you prefer manual testing instead of automated testing:

### 5.2 Test Individual Tasks Manually

In Task Scheduler (AHSkripts folder):
1. Right-click **"Status Web App"** → **"Run"**
2. Wait 3-5 seconds
3. Check if State changes to **"Running"**
4. Repeat for other tasks

**Note:** Manual testing does not verify Service account credentials as thoroughly as automated testing.

### 5.3 Verify Services are Running

```powershell
# Check if tasks are running
Get-ScheduledTask -TaskPath "\AHSkripts\" | Where-Object {$_.State -eq "Running"} | Select-Object TaskName

# Check Python processes
Get-Process python -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count
# Should return: 3 (one for each service)
```

### 5.4 Check Log Files

**Starter Script Logs (in `logs\` directory):**
```powershell
# Check Flask Web App log
Get-Content "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs\app_2025-10.log" -Tail 10

# Check DSL Speedtest log
Get-Content "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs\status_dsl_2025-10.log" -Tail 10

# Check Stock Monitoring log
Get-Content "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs\status_2025-10.log" -Tail 10
```

**Expected log entries:**
```
[2025-10-22 10:35:31] Starting Flask Web Application
[2025-10-22 10:35:31] Running as user: Service
[2025-10-22 10:35:31] Changed directory to: \\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status
[2025-10-22 10:35:31] Starting Flask application (app.py)...
```

**Check Error Logs (if any):**
```powershell
Get-ChildItem "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs\*_errors_*.log" -ErrorAction SilentlyContinue
# Should return: Nothing (no error logs = no errors)
```

**Python Script Logs (in root directory):**
- `status_dsl.log` - DSL speedtest monitoring logs (configured in `status_dsl.ini`)
- Python scripts may create their own logs based on INI configuration

### 5.5 Verify Web Dashboard

1. Open browser
2. Navigate to: `http://[server-ip]:5000` or `http://localhost:5000`
3. You should see the portfolio monitoring dashboard
4. Verify data is loading correctly

### 5.6 Verify Data Files

```powershell
# Check JSON output files
Get-Item "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\static\depotdaten.json" | Select-Object Name, Length, LastWriteTime

Get-Item "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\static\speedtest.json" | Select-Object Name, Length, LastWriteTime

# Files should be recently updated
```

### 5.7 Server Restart Test

**Final verification:**
1. Restart the server: `Restart-Computer`
2. Wait 5-10 minutes after boot
3. Check Task Scheduler → All tasks should be **"Running"**
4. Verify web dashboard is accessible
5. Check log files for successful startup

## Step 6: Maintenance and Monitoring

### 6.1 Log File Management

**Automatic:**
- Log files older than **120 days** are automatically deleted by PowerShell scripts
- Monthly rotation: `app_2025-10.log`, `app_2025-11.log`, etc.
- Separate error logs: `*_errors_YYYY-MM.log`

**Manual Monitoring:**
```powershell
# View current month logs
Get-ChildItem "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs" -Filter "*_2025-10.log"

# Check log sizes
Get-ChildItem "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs" |
    Select-Object Name, @{Name="SizeMB";Expression={[math]::Round($_.Length/1MB, 2)}} |
    Sort-Object SizeMB -Descending
```

### 6.2 Regular Maintenance Tasks

**Weekly:**
- Check Task Scheduler history for failures
- Verify all 3 tasks are **"Running"**
- Monitor disk space in `logs\` directory

**Monthly:**
- Review error logs (if any): `*_errors_*.log`
- Check Python script logs for unusual activity
- Verify data files are being updated

**As Needed:**
- Update repository: `git pull origin main`
- Restart services via Task Scheduler if needed
- Update Python dependencies: `pip install -r requirements.txt --upgrade`

### 6.3 Monitoring Commands

**Quick Status Check:**
```powershell
# Check all tasks in AHSkripts folder
Get-ScheduledTask -TaskPath "\AHSkripts\" | Select-Object TaskName, State, LastRunTime | Format-Table -AutoSize

# Check Python processes
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, StartTime, CPU

# Check recent log updates
Get-ChildItem "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs\*_2025-*.log" |
    Select-Object Name, LastWriteTime |
    Sort-Object LastWriteTime -Descending
```

**Detailed Status Script:**
```powershell
Write-Host "=== Service Status Check ===" -ForegroundColor Cyan

# 1. Task Status
Write-Host "`nTask Scheduler Status:" -ForegroundColor Yellow
Get-ScheduledTask -TaskPath "\AHSkripts\" | Select-Object TaskName, State | Format-Table

# 2. Log Files
Write-Host "Recent Log Activity:" -ForegroundColor Yellow
$currentMonth = Get-Date -Format "yyyy-MM"
Get-ChildItem "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\logs" -Filter "*_$currentMonth.log" |
    Select-Object Name, @{Name="SizeKB";Expression={[math]::Round($_.Length/1KB, 2)}}, LastWriteTime |
    Format-Table

# 3. Data Files
Write-Host "Data File Updates:" -ForegroundColor Yellow
Get-Item "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status\static\*.json" |
    Select-Object Name, LastWriteTime |
    Format-Table

# 4. Python Processes
Write-Host "Running Python Processes:" -ForegroundColor Yellow
$pythonCount = (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "Active Python processes: $pythonCount (Expected: 3)"

Write-Host "`n=== Check Complete ===" -ForegroundColor Cyan
```

## Step 7: Troubleshooting

### 7.1 Tasks Not Starting

**Symptom:** Tasks show "Ready" but don't run

**Solutions:**
1. Check Service account password is correct
2. Verify "Log on as a service" right is granted
3. Check folder permissions (Service account needs full control)
4. Review Task History in Task Scheduler for error messages
5. Check Windows Event Viewer → Windows Logs → System

### 7.2 UNC Path Access Denied

**Symptom:** Logs show "Access Denied" or "Path not found"

**Solutions:**
1. Verify Service account has network share access
2. Check NTFS permissions on network share
3. Test manually: `Test-Path "\\WIN-H7BKO5H0RMC\Dataserver"`
4. Ensure network is available before tasks start (use delays)

### 7.3 Python Script Errors

**Symptom:** Tasks start but Python scripts fail

**Solutions:**
1. Check Python script logs for specific errors
2. Verify virtual environment exists: `.venv\Scripts\python.exe`
3. Ensure all dependencies installed: `pip install -r requirements.txt`
4. Check INI configuration files
5. Review error logs: `logs\*_errors_*.log`

### 7.4 Network Resources Not Available

**Symptom:** Stock Monitoring Service fails to find Excel files

**Solutions:**
1. Increase network wait timeout in `start_status.ps1`:
   ```powershell
   $MAX_NETWORK_WAIT = 60  # Increase from 60 to 120
   ```
2. Increase Task Scheduler startup delay (currently 2 minutes)
3. Check network share is online: `\\WIN-H7BKO5H0RMC\Dataserver`
4. Verify Excel files exist at expected paths

### 7.5 Port 5000 Already in Use

**Symptom:** Flask app fails to start with "Address already in use"

**Solutions:**
1. Check if another process uses port 5000:
   ```powershell
   Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
   ```
2. Change Flask port in `app.py` if needed
3. Update firewall rule for new port

### 7.6 Emergency Logs in C:\Temp

**Symptom:** Logs appear in `C:\Temp\*_emergency_*.log`

**Meaning:** PowerShell scripts couldn't write to `logs\` directory

**Solutions:**
1. Check `logs\` directory exists
2. Verify Service account has write permissions
3. Check disk space availability
4. Review emergency logs for specific error messages

### 7.7 Task History Shows Errors

**Check Task History:**
1. Open Task Scheduler
2. Navigate to task
3. Click **"History"** tab
4. Look for error events (Event ID 103, 203)

**Common Error Codes:**
- `0x1` - General error (check logs)
- `0x2` - File not found
- `0x3` - Path not found
- `0x267009` - Task is running (not an error)

## System Requirements

### Minimum Requirements
- **CPU:** 2 cores (services are lightweight)
- **RAM:** 2GB available (512MB per service)
- **Disk:** 20GB free space (for data accumulation and logs)
- **Network:** Stable internet connection for price/speedtest APIs
- **Python:** Version 3.8 or higher
- **OS:** Windows Server 2016 or higher

### Recommended Requirements
- **CPU:** 4 cores
- **RAM:** 4GB available
- **Disk:** 50GB+ free space (SSD preferred)
- **Network:** 10+ Mbps internet connection

## Service Startup Order

The services start in a staggered sequence to ensure reliable operation:

1. **Flask Web App** - Immediate startup (0 minutes delay)
2. **Stock Monitor** - 2 minutes delay (wait for network shares)
3. **DSL Speedtest** - 3 minutes delay (prevent resource conflicts)

This approach ensures:
- Network resources are available before Stock Monitor starts
- Services don't compete for resources during startup
- Web dashboard is available as soon as possible

## Security Considerations

### Access Control
- Service account has minimal required permissions (not Administrator)
- Web dashboard only accessible on port 5000 (configure firewall rules)
- No credentials stored in scripts or configuration files
- Log files contain no sensitive information

### Network Security
- External file access limited to specified network paths
- UNC paths use Windows authentication (no passwords in scripts)
- Service account password only required during task registration

### Data Protection
- Portfolio data stored in Parquet format (compressed)
- JSON output files refreshed periodically (no historical sensitive data)
- Log rotation prevents disk space exhaustion
- Automatic cleanup of old logs (120 days)

## Data Files and Locations

### Configuration Files (Root Directory)
- `status.ini` - Stock monitoring configuration
- `status_dsl.ini` - DSL speedtest configuration
- `dsl_speedtest_viewer.ini` - Speedtest viewer configuration
- `requirements.txt` - Python dependencies

### Data Files (Root Directory)
- `prices.parquet` - Historical stock price data
- `speedtest_data.parquet` - Historical DSL speedtest data

### Output Files (static/ Directory)
- `static/depotdaten.json` - Real-time portfolio data for web dashboard
- `static/speedtest.json` - Current speedtest results

### Log Files (logs/ Directory)
- `logs/app_YYYY-MM.log` - Flask Web App logs (monthly)
- `logs/status_YYYY-MM.log` - Stock Monitoring logs (monthly)
- `logs/status_dsl_YYYY-MM.log` - DSL Speedtest logs (monthly)
- `logs/*_errors_YYYY-MM.log` - Error logs (if errors occur)

### Python Script Logs (Root Directory)
- `status_dsl.log` - DSL monitoring script logs (configured in INI)
- May be configured to write to `logs\` directory

## Backup and Restore

### Configuration Backup

**Backup Task Configurations:**
```powershell
# Export all tasks in AHSkripts folder
Get-ScheduledTask -TaskPath "\AHSkripts\" | ForEach-Object {
    $taskName = $_.TaskName
    Export-ScheduledTask -TaskName $taskName -TaskPath "\AHSkripts\" |
        Out-File "D:\Backups\$taskName.xml" -Encoding UTF8
}
```

**Restore Task Configuration:**
```powershell
# Import task from XML
Register-ScheduledTask -Xml (Get-Content "D:\Backups\Status Web App.xml" | Out-String) `
    -TaskName "Status Web App" `
    -TaskPath "\AHSkripts\" `
    -User "Service" `
    -Password "YourPassword"
```

### Data Backup

**Important files to backup regularly:**
- `prices.parquet` - Stock price history
- `speedtest_data.parquet` - Speedtest history
- Configuration files (`*.ini`)
- PowerShell scripts (`*.ps1`)

## Updates and Version Control

### Updating the System

1. **Stop all tasks:**
   ```powershell
   Get-ScheduledTask -TaskPath "\AHSkripts\" | Stop-ScheduledTask
   ```

2. **Pull latest code:**
   ```cmd
   cd \\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status
   git pull origin main
   ```

3. **Update dependencies:**
   ```cmd
   .venv\Scripts\activate
   pip install -r requirements.txt --upgrade
   ```

4. **Restart tasks:**
   ```powershell
   Get-ScheduledTask -TaskPath "\AHSkripts\" | Start-ScheduledTask
   ```

### Version History

- **Version 2.0 (2025-10-22):** PowerShell-based deployment with centralized logging
- **Version 1.0:** Original Batch-based deployment

## Support and References

### Log Locations
- **Starter Script Logs:** `logs\*_YYYY-MM.log`
- **Error Logs:** `logs\*_errors_YYYY-MM.log`
- **Python Logs:** Root directory (configurable via INI files)

### Performance Monitoring
- Use DSL Speedtest Viewer: `python dsl_speedtest_viewer.py`
- Monitor Task Scheduler history
- Review Windows Event Viewer → System logs

### Documentation
- **CHANGELOG_2025-10-22.md** - Recent changes and test results
- **CHANGELOG_2025-10-20.md** - UNC path problem resolution
- **CHANGELOG_2025-10-17.md** - Network wait logic implementation
- **README.md** - Project overview
- **CLAUDE.md** - Development guidelines

### Getting Help

If issues persist:
1. Check all CHANGELOG files for known issues and solutions
2. Review error logs: `logs\*_errors_*.log`
3. Check Task Scheduler history for error codes
4. Review Windows Event Viewer for system-level issues
5. Consult deployment scripts in `_Archiv\` for rollback options

---

**Document Version:** 2.0
**Last Updated:** 2025-10-22
**Deployment Status:** Tested and verified with Service account
**All Services:** Running and operational
