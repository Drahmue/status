# Automated Service-User Testing Script
# Tests all three PowerShell starter scripts as the Service user
# Version: 2025-10-22

#Requires -RunAsAdministrator

param(
    [string]$ServiceUser = "Service",
    [switch]$CleanupAfterTest = $true
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$scriptDir = "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status"
$testLogFile = "$scriptDir\logs\service_test_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').log"
$testResults = @()

function Write-TestLog {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    $logMessage = "$timestamp [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $testLogFile -Value $logMessage -ErrorAction SilentlyContinue
}

Write-TestLog "=== Starting Automated Service-User Tests ===" "INFO"
Write-TestLog "Current User: $env:USERNAME" "INFO"
Write-TestLog "Service User: $ServiceUser" "INFO"
Write-TestLog "Script Directory: $scriptDir" "INFO"

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-TestLog "ERROR: This script must be run as Administrator!" "ERROR"
    exit 1
}

# Define test scripts
$testScripts = @(
    @{
        Name = "Flask Web App"
        Script = "start_app.ps1"
        LogFile = "logs\app_2025-10.log"
        ErrorLog = "logs\app_errors_2025-10.log"
        TaskName = "Test_App_Service"
        Timeout = 15
    },
    @{
        Name = "DSL Speedtest Monitoring"
        Script = "start_status_dsl.ps1"
        LogFile = "logs\status_dsl_2025-10.log"
        ErrorLog = "logs\status_dsl_errors_2025-10.log"
        TaskName = "Test_DSL_Service"
        Timeout = 15
    },
    @{
        Name = "Stock Monitoring Service"
        Script = "start_status.ps1"
        LogFile = "logs\status_2025-10.log"
        ErrorLog = "logs\status_errors_2025-10.log"
        TaskName = "Test_Status_Service"
        Timeout = 15
    }
)

Write-TestLog "--- Phase 1: Creating Test Tasks ---" "INFO"

foreach ($test in $testScripts) {
    Write-TestLog "Creating test task: $($test.TaskName)" "INFO"

    # Delete existing test task if it exists
    $existingTask = Get-ScheduledTask -TaskName $test.TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-TestLog "Removing existing test task: $($test.TaskName)" "INFO"
        Unregister-ScheduledTask -TaskName $test.TaskName -Confirm:$false
    }

    # Create test task action
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -File `"$scriptDir\$($test.Script)`""

    # Create task principal (run as Service user)
    $principal = New-ScheduledTaskPrincipal `
        -UserId $ServiceUser `
        -LogonType ServiceAccount `
        -RunLevel Highest

    # Create task settings
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

    # Register the task
    try {
        Register-ScheduledTask `
            -TaskName $test.TaskName `
            -Action $action `
            -Principal $principal `
            -Settings $settings `
            -Description "Temporary test task for $($test.Name) as Service user" `
            -ErrorAction Stop | Out-Null

        Write-TestLog "Test task created: $($test.TaskName)" "SUCCESS"
    } catch {
        Write-TestLog "Failed to create test task: $($_.Exception.Message)" "ERROR"
        $testResults += @{
            Name = $test.Name
            Status = "FAILED"
            Reason = "Could not create test task: $($_.Exception.Message)"
        }
        continue
    }
}

Write-TestLog "" "INFO"
Write-TestLog "--- Phase 2: Running Tests ---" "INFO"

foreach ($test in $testScripts) {
    Write-TestLog "Testing: $($test.Name)" "INFO"

    # Check if task was created
    $task = Get-ScheduledTask -TaskName $test.TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-TestLog "Test task not found, skipping" "ERROR"
        continue
    }

    # Get current log file size (if exists) to detect new entries
    $logPath = "$scriptDir\$($test.LogFile)"
    $preTestLogSize = 0
    if (Test-Path $logPath) {
        $preTestLogSize = (Get-Item $logPath).Length
    }

    # Start the task
    Write-TestLog "  Starting task: $($test.TaskName)" "INFO"
    try {
        Start-ScheduledTask -TaskName $test.TaskName -ErrorAction Stop
        Write-TestLog "  Task started, waiting $($test.Timeout) seconds..." "INFO"

        # Wait for the script to initialize
        Start-Sleep -Seconds $test.Timeout

        # Check if task is running
        $taskInfo = Get-ScheduledTask -TaskName $test.TaskName
        $taskState = $taskInfo.State
        Write-TestLog "  Task state: $taskState" "INFO"

        # Stop the task (since these scripts run continuously)
        Write-TestLog "  Stopping task..." "INFO"
        Stop-ScheduledTask -TaskName $test.TaskName -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2

        # Analyze results
        $success = $true
        $reasons = @()

        # Check 1: Log file created
        if (Test-Path $logPath) {
            $postTestLogSize = (Get-Item $logPath).Length
            if ($postTestLogSize -gt $preTestLogSize) {
                Write-TestLog "  Log file created/updated: $($test.LogFile)" "SUCCESS"

                # Read last 10 lines of log
                $logContent = Get-Content $logPath -Tail 10 -ErrorAction SilentlyContinue
                Write-TestLog "  Log content (last 10 lines):" "INFO"
                foreach ($line in $logContent) {
                    Write-TestLog "    $line" "INFO"
                }

                # Check for Service user in log
                $serviceUserFound = $logContent | Where-Object { $_ -match "Service" }
                if ($serviceUserFound) {
                    Write-TestLog "  Service user confirmed in log" "SUCCESS"
                } else {
                    Write-TestLog "  Service user not found in log" "WARNING"
                }
            } else {
                Write-TestLog "  Log file not updated" "ERROR"
                $success = $false
                $reasons += "Log file not updated"
            }
        } else {
            Write-TestLog "  Log file not created: $logPath" "ERROR"
            $success = $false
            $reasons += "Log file not created"
        }

        # Check 2: Error log
        $errorLogPath = "$scriptDir\$($test.ErrorLog)"
        if (Test-Path $errorLogPath) {
            $errorContent = Get-Content $errorLogPath -ErrorAction SilentlyContinue
            if ($errorContent -and $errorContent.Count -gt 0) {
                Write-TestLog "  Error log contains entries:" "WARNING"
                foreach ($line in ($errorContent | Select-Object -Last 5)) {
                    Write-TestLog "    $line" "WARNING"
                }
                $reasons += "Error log has entries (may be normal)"
            } else {
                Write-TestLog "  No error log entries" "SUCCESS"
            }
        } else {
            Write-TestLog "  No error log created" "SUCCESS"
        }

        # Record result
        $testResults += @{
            Name = $test.Name
            Status = if ($success) { "PASSED" } else { "FAILED" }
            Reasons = $reasons -join "; "
            LogFile = $test.LogFile
            TaskState = $taskState
        }

        if ($success) {
            Write-TestLog "Test PASSED: $($test.Name)" "SUCCESS"
        } else {
            Write-TestLog "Test FAILED: $($test.Name) - $($reasons -join '; ')" "ERROR"
        }

    } catch {
        Write-TestLog "Error running test: $($_.Exception.Message)" "ERROR"
        $testResults += @{
            Name = $test.Name
            Status = "FAILED"
            Reasons = "Exception: $($_.Exception.Message)"
        }
    }

    Write-TestLog "" "INFO"
}

Write-TestLog "--- Phase 3: Cleanup ---" "INFO"

if ($CleanupAfterTest) {
    foreach ($test in $testScripts) {
        $task = Get-ScheduledTask -TaskName $test.TaskName -ErrorAction SilentlyContinue
        if ($task) {
            Write-TestLog "Removing test task: $($test.TaskName)" "INFO"
            Unregister-ScheduledTask -TaskName $test.TaskName -Confirm:$false
        }
    }
    Write-TestLog "Test tasks cleaned up" "SUCCESS"
} else {
    Write-TestLog "Test tasks NOT removed (CleanupAfterTest = false)" "WARNING"
}

Write-TestLog "" "INFO"
Write-TestLog "=== Test Results Summary ===" "INFO"
Write-TestLog "" "INFO"

$passedCount = 0
$failedCount = 0

foreach ($result in $testResults) {
    $status = $result.Status
    $symbol = if ($status -eq "PASSED") { "[PASS]" } else { "[FAIL]" }
    $level = if ($status -eq "PASSED") { "SUCCESS" } else { "ERROR" }

    Write-TestLog "$symbol $($result.Name): $status" $level
    if ($result.Reasons) {
        Write-TestLog "  Reason: $($result.Reasons)" $level
    }
    if ($result.LogFile) {
        Write-TestLog "  Log: $($result.LogFile)" "INFO"
    }

    if ($status -eq "PASSED") {
        $passedCount++
    } else {
        $failedCount++
    }
}

Write-TestLog "" "INFO"
Write-TestLog "Total: $($testResults.Count) tests" "INFO"
Write-TestLog "Passed: $passedCount" "SUCCESS"
Write-TestLog "Failed: $failedCount" $(if ($failedCount -gt 0) { "ERROR" } else { "SUCCESS" })
Write-TestLog "" "INFO"
Write-TestLog "Test log saved to: $testLogFile" "INFO"
Write-TestLog "=== Testing Complete ===" "INFO"

# Exit with appropriate code
if ($failedCount -gt 0) {
    exit 1
} else {
    exit 0
}
