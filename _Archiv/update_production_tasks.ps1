# Update Production Tasks to PowerShell Scripts
# Updates "Status Web App" and "DSL Speedtest Monitoring" tasks
# Version: 2025-10-22

#Requires -RunAsAdministrator

param(
    [string]$ServiceUser = "Service"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$scriptDir = "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status"
$logFile = "$scriptDir\logs\task_update_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "[yyyy-MM-dd HH:mm:ss]"
    $logMessage = "$timestamp [$Level] $Message"

    $color = switch ($Level) {
        "SUCCESS" { "Green" }
        "ERROR" { "Red" }
        "WARNING" { "Yellow" }
        default { "White" }
    }

    Write-Host $logMessage -ForegroundColor $color
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  PRODUCTION TASK UPDATE" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Write-Log "=== Starting Production Task Update ===" "INFO"
Write-Log "Current User: $env:USERNAME" "INFO"
Write-Log "Service User: $ServiceUser" "INFO"
Write-Log "Script Directory: $scriptDir" "INFO"

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Log "ERROR: This script must be run as Administrator!" "ERROR"
    exit 1
}

# Get credentials for Service user
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PASSWORD REQUIRED" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Please enter the password for user: $ServiceUser" -ForegroundColor White
Write-Host ""

$credential = Get-Credential -UserName $ServiceUser -Message "Enter password for Service user to update production tasks"

if (-not $credential) {
    Write-Log "ERROR: No credentials provided. Exiting." "ERROR"
    exit 1
}

$password = $credential.GetNetworkCredential().Password
Write-Log "Credentials received for user: $ServiceUser" "SUCCESS"

# Define tasks to update
$tasksToUpdate = @(
    @{
        TaskName = "Status Web App"
        Script = "start_app.ps1"
        Description = "Flask Web Application Service - Serves portfolio monitoring dashboard on http://localhost:5000"
        BackupName = "Status Web App (OLD BATCH)"
    },
    @{
        TaskName = "DSL Speedtest Monitoring"
        Script = "start_status_dsl.ps1"
        Description = "DSL Speedtest Monitoring Service - Continuous internet speed monitoring with Ookla CLI"
        BackupName = "DSL Speedtest Monitoring (OLD BATCH)"
    }
)

Write-Log "" "INFO"
Write-Log "--- Phase 1: Backup Existing Tasks ---" "INFO"

foreach ($taskDef in $tasksToUpdate) {
    Write-Log "Processing task: $($taskDef.TaskName)" "INFO"

    # Check if task exists
    $existingTask = Get-ScheduledTask -TaskName $taskDef.TaskName -ErrorAction SilentlyContinue

    if (-not $existingTask) {
        Write-Log "  WARNING: Task '$($taskDef.TaskName)' not found! Skipping backup." "WARNING"
        continue
    }

    # Export current task as XML backup
    $backupPath = "$scriptDir\_Archiv\$($taskDef.TaskName)_backup_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').xml"

    try {
        Export-ScheduledTask -TaskName $taskDef.TaskName | Out-File -FilePath $backupPath -Encoding UTF8
        Write-Log "  Backup created: $backupPath" "SUCCESS"
    } catch {
        Write-Log "  WARNING: Could not create backup: $($_.Exception.Message)" "WARNING"
    }

    # Get current task info
    $taskInfo = Get-ScheduledTaskInfo -TaskName $taskDef.TaskName
    Write-Log "  Current task state: $($existingTask.State)" "INFO"
    Write-Log "  Last run: $($taskInfo.LastRunTime)" "INFO"
    Write-Log "  Last result: $($taskInfo.LastTaskResult)" "INFO"

    # Check if task is currently running
    if ($existingTask.State -eq "Running") {
        Write-Host ""
        Write-Host "  WARNING: Task '$($taskDef.TaskName)' is currently RUNNING!" -ForegroundColor Yellow
        Write-Host "  The task will be stopped and reconfigured." -ForegroundColor Yellow
        Write-Host ""
        $response = Read-Host "  Do you want to continue? (yes/no)"

        if ($response -ne "yes") {
            Write-Log "  User cancelled update for task: $($taskDef.TaskName)" "WARNING"
            continue
        }

        # Stop the running task
        Write-Log "  Stopping running task..." "INFO"
        Stop-ScheduledTask -TaskName $taskDef.TaskName -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Log "  Task stopped" "SUCCESS"
    }
}

Write-Log "" "INFO"
Write-Log "--- Phase 2: Update Tasks ---" "INFO"

$updateResults = @()

foreach ($taskDef in $tasksToUpdate) {
    Write-Log "Updating task: $($taskDef.TaskName)" "INFO"

    # Check if task exists
    $existingTask = Get-ScheduledTask -TaskName $taskDef.TaskName -ErrorAction SilentlyContinue

    if (-not $existingTask) {
        Write-Log "  ERROR: Task not found, cannot update!" "ERROR"
        $updateResults += @{
            TaskName = $taskDef.TaskName
            Status = "FAILED"
            Reason = "Task not found"
        }
        continue
    }

    try {
        # Get existing trigger and settings
        $trigger = $existingTask.Triggers[0]
        $settings = $existingTask.Settings

        # Create new action for PowerShell script
        $newAction = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-ExecutionPolicy Bypass -File `"$scriptDir\$($taskDef.Script)`""

        Write-Log "  New action: powershell.exe -ExecutionPolicy Bypass -File `"$scriptDir\$($taskDef.Script)`"" "INFO"

        # Unregister old task
        Write-Log "  Unregistering old task..." "INFO"
        Unregister-ScheduledTask -TaskName $taskDef.TaskName -Confirm:$false

        # Register new task with PowerShell script
        Write-Log "  Registering updated task..." "INFO"
        Register-ScheduledTask `
            -TaskName $taskDef.TaskName `
            -Action $newAction `
            -Trigger $trigger `
            -Settings $settings `
            -User $ServiceUser `
            -Password $password `
            -RunLevel Highest `
            -Description $taskDef.Description `
            -ErrorAction Stop | Out-Null

        Write-Log "  Task updated successfully!" "SUCCESS"

        $updateResults += @{
            TaskName = $taskDef.TaskName
            Status = "SUCCESS"
            Script = $taskDef.Script
        }

    } catch {
        Write-Log "  ERROR: Failed to update task: $($_.Exception.Message)" "ERROR"
        $updateResults += @{
            TaskName = $taskDef.TaskName
            Status = "FAILED"
            Reason = $_.Exception.Message
        }
    }

    Write-Log "" "INFO"
}

Write-Log "--- Phase 3: Verify Updates ---" "INFO"

foreach ($taskDef in $tasksToUpdate) {
    $task = Get-ScheduledTask -TaskName $taskDef.TaskName -ErrorAction SilentlyContinue

    if ($task) {
        Write-Log "Task: $($taskDef.TaskName)" "INFO"
        Write-Log "  State: $($task.State)" "INFO"
        Write-Log "  Action: $($task.Actions[0].Execute) $($task.Actions[0].Arguments)" "INFO"
        Write-Log "  User: $($task.Principal.UserId)" "INFO"

        # Check if it's using PowerShell
        if ($task.Actions[0].Execute -like "*powershell.exe*") {
            Write-Log "  Status: Updated to PowerShell" "SUCCESS"
        } else {
            Write-Log "  WARNING: Not using PowerShell!" "WARNING"
        }
    } else {
        Write-Log "Task '$($taskDef.TaskName)' not found!" "ERROR"
    }

    Write-Log "" "INFO"
}

Write-Log "--- Phase 4: Start Updated Tasks ---" "INFO"

Write-Host ""
Write-Host "Do you want to start the updated tasks now? (yes/no)" -ForegroundColor Yellow
$startNow = Read-Host

if ($startNow -eq "yes") {
    foreach ($result in $updateResults) {
        if ($result.Status -eq "SUCCESS") {
            Write-Log "Starting task: $($result.TaskName)" "INFO"

            try {
                Start-ScheduledTask -TaskName $result.TaskName -ErrorAction Stop
                Start-Sleep -Seconds 2

                $taskState = (Get-ScheduledTask -TaskName $result.TaskName).State
                Write-Log "  Task started. State: $taskState" "SUCCESS"

                # Check log file
                $logPattern = switch ($result.Script) {
                    "start_app.ps1" { "app_*.log" }
                    "start_status_dsl.ps1" { "status_dsl_*.log" }
                    default { "*.log" }
                }

                Start-Sleep -Seconds 3

                $logFiles = Get-ChildItem "$scriptDir\logs\$logPattern" -ErrorAction SilentlyContinue |
                    Sort-Object LastWriteTime -Descending |
                    Select-Object -First 1

                if ($logFiles) {
                    Write-Log "  Log file: $($logFiles.Name)" "INFO"
                    $logContent = Get-Content $logFiles.FullName -Tail 5 -ErrorAction SilentlyContinue
                    foreach ($line in $logContent) {
                        Write-Log "    $line" "INFO"
                    }
                }

            } catch {
                Write-Log "  ERROR: Failed to start task: $($_.Exception.Message)" "ERROR"
            }

            Write-Log "" "INFO"
        }
    }
} else {
    Write-Log "Tasks not started. You can start them manually from Task Scheduler." "INFO"
}

Write-Log "" "INFO"
Write-Log "=== Update Results Summary ===" "INFO"
Write-Log "" "INFO"

$successCount = 0
$failedCount = 0

foreach ($result in $updateResults) {
    $status = $result.Status
    $symbol = if ($status -eq "SUCCESS") { "[OK]" } else { "[FAIL]" }
    $level = if ($status -eq "SUCCESS") { "SUCCESS" } else { "ERROR" }

    Write-Log "$symbol $($result.TaskName): $status" $level
    if ($result.Script) {
        Write-Log "  New script: $($result.Script)" "INFO"
    }
    if ($result.Reason) {
        Write-Log "  Reason: $($result.Reason)" $level
    }

    if ($status -eq "SUCCESS") {
        $successCount++
    } else {
        $failedCount++
    }
}

Write-Log "" "INFO"
Write-Log "Total: $($updateResults.Count) tasks" "INFO"
Write-Log "Updated successfully: $successCount" "SUCCESS"
Write-Log "Failed: $failedCount" $(if ($failedCount -gt 0) { "ERROR" } else { "SUCCESS" })
Write-Log "" "INFO"
Write-Log "Log file saved to: $logFile" "INFO"
Write-Log "Backups saved to: $scriptDir\_Archiv\" "INFO"
Write-Log "" "INFO"
Write-Log "=== Update Complete ===" "INFO"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  UPDATE COMPLETE" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "Green" })
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Updated: $successCount / Failed: $failedCount" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: Stock Monitoring Service already uses PowerShell" -ForegroundColor Yellow
Write-Host "           and does not need to be updated." -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Check Task Scheduler to verify tasks are configured correctly" -ForegroundColor White
Write-Host "2. Monitor log files in logs\ directory" -ForegroundColor White
Write-Host "3. Perform server restart test when ready" -ForegroundColor White
Write-Host ""

# Exit with appropriate code
if ($failedCount -gt 0) {
    exit 1
} else {
    exit 0
}
