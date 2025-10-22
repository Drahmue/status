# Move Tasks to AHSkripts Folder
# Moves "Status Web App" and "DSL Speedtest Monitoring" from root to \AHSkripts\
# Version: 2025-10-22

#Requires -RunAsAdministrator

param(
    [string]$ServiceUser = "Service",
    [string]$TargetFolder = "AHSkripts"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$scriptDir = "\\WIN-H7BKO5H0RMC\Dataserver\_Batchprozesse\status"
$logFile = "$scriptDir\logs\task_move_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').log"

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
Write-Host "  MOVE TASKS TO AHSKRIPTS FOLDER" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Write-Log "=== Starting Task Move Operation ===" "INFO"
Write-Log "Current User: $env:USERNAME" "INFO"
Write-Log "Service User: $ServiceUser" "INFO"
Write-Log "Target Folder: \$TargetFolder\" "INFO"

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

$credential = Get-Credential -UserName $ServiceUser -Message "Enter password for Service user to move tasks"

if (-not $credential) {
    Write-Log "ERROR: No credentials provided. Exiting." "ERROR"
    exit 1
}

$password = $credential.GetNetworkCredential().Password
Write-Log "Credentials received for user: $ServiceUser" "SUCCESS"

# Define tasks to move
$tasksToMove = @(
    @{
        TaskName = "Status Web App"
        CurrentPath = "\"
        Description = "Flask Web Application Service - Serves portfolio monitoring dashboard on http://localhost:5000"
    },
    @{
        TaskName = "DSL Speedtest Monitoring"
        CurrentPath = "\"
        Description = "DSL Speedtest Monitoring Service - Continuous internet speed monitoring with Ookla CLI"
    }
)

Write-Log "" "INFO"
Write-Log "--- Phase 1: Check Current Location ---" "INFO"

$tasksFound = @()

foreach ($taskDef in $tasksToMove) {
    $task = Get-ScheduledTask -TaskName $taskDef.TaskName -ErrorAction SilentlyContinue

    if ($task) {
        Write-Log "Task found: $($taskDef.TaskName)" "SUCCESS"
        Write-Log "  Current path: $($task.TaskPath)" "INFO"
        Write-Log "  Current state: $($task.State)" "INFO"

        $tasksFound += @{
            TaskName = $taskDef.TaskName
            Task = $task
            Description = $taskDef.Description
        }

        if ($task.TaskPath -eq "\$TargetFolder\") {
            Write-Log "  NOTE: Task is already in target folder!" "WARNING"
        }
    } else {
        Write-Log "Task NOT found: $($taskDef.TaskName)" "ERROR"
    }
}

if ($tasksFound.Count -eq 0) {
    Write-Log "ERROR: No tasks found to move!" "ERROR"
    exit 1
}

Write-Log "" "INFO"
Write-Log "--- Phase 2: Create Target Folder ---" "INFO"

# Check if AHSkripts folder exists
$folderExists = $false
try {
    $existingTasks = Get-ScheduledTask -TaskPath "\$TargetFolder\" -ErrorAction SilentlyContinue
    $folderExists = $true
    Write-Log "Folder '\$TargetFolder\' already exists" "SUCCESS"
} catch {
    Write-Log "Folder '\$TargetFolder\' does not exist, will be created automatically" "INFO"
}

Write-Log "" "INFO"
Write-Log "--- Phase 3: Export Tasks ---" "INFO"

$exportedTasks = @()

foreach ($taskInfo in $tasksFound) {
    Write-Log "Exporting task: $($taskInfo.TaskName)" "INFO"

    try {
        # Export task to XML
        $xmlContent = Export-ScheduledTask -TaskName $taskInfo.TaskName

        # Backup to archive
        $backupPath = "$scriptDir\_Archiv\$($taskInfo.TaskName)_before_move_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').xml"
        $xmlContent | Out-File -FilePath $backupPath -Encoding UTF8
        Write-Log "  Backup created: $backupPath" "SUCCESS"

        $exportedTasks += @{
            TaskName = $taskInfo.TaskName
            Task = $taskInfo.Task
            XmlContent = $xmlContent
            Description = $taskInfo.Description
        }

    } catch {
        Write-Log "  ERROR: Failed to export task: $($_.Exception.Message)" "ERROR"
    }
}

if ($exportedTasks.Count -eq 0) {
    Write-Log "ERROR: No tasks were exported!" "ERROR"
    exit 1
}

Write-Log "" "INFO"
Write-Log "--- Phase 4: Stop Running Tasks ---" "INFO"

foreach ($taskInfo in $exportedTasks) {
    $currentState = (Get-ScheduledTask -TaskName $taskInfo.TaskName).State

    if ($currentState -eq "Running") {
        Write-Log "Stopping task: $($taskInfo.TaskName)" "INFO"
        Stop-ScheduledTask -TaskName $taskInfo.TaskName -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Log "  Task stopped" "SUCCESS"
    } else {
        Write-Log "Task '$($taskInfo.TaskName)' is not running (State: $currentState)" "INFO"
    }
}

Write-Log "" "INFO"
Write-Log "--- Phase 5: Delete Tasks from Root ---" "INFO"

foreach ($taskInfo in $exportedTasks) {
    Write-Log "Deleting task from root: $($taskInfo.TaskName)" "INFO"

    try {
        Unregister-ScheduledTask -TaskName $taskInfo.TaskName -Confirm:$false
        Write-Log "  Task deleted from root" "SUCCESS"
    } catch {
        Write-Log "  ERROR: Failed to delete task: $($_.Exception.Message)" "ERROR"
    }
}

Write-Log "" "INFO"
Write-Log "--- Phase 6: Register Tasks in AHSkripts Folder ---" "INFO"

$moveResults = @()

foreach ($taskInfo in $exportedTasks) {
    Write-Log "Registering task in '\$TargetFolder\': $($taskInfo.TaskName)" "INFO"

    try {
        # Get task components
        $action = $taskInfo.Task.Actions[0]
        $triggers = $taskInfo.Task.Triggers
        $settings = $taskInfo.Task.Settings

        # Register task in new location
        Register-ScheduledTask `
            -TaskName $taskInfo.TaskName `
            -TaskPath "\$TargetFolder\" `
            -Action $action `
            -Trigger $triggers `
            -Settings $settings `
            -User $ServiceUser `
            -Password $password `
            -RunLevel Highest `
            -Description $taskInfo.Description `
            -ErrorAction Stop | Out-Null

        Write-Log "  Task registered successfully!" "SUCCESS"

        $moveResults += @{
            TaskName = $taskInfo.TaskName
            Status = "SUCCESS"
        }

    } catch {
        Write-Log "  ERROR: Failed to register task: $($_.Exception.Message)" "ERROR"

        $moveResults += @{
            TaskName = $taskInfo.TaskName
            Status = "FAILED"
            Reason = $_.Exception.Message
        }
    }
}

Write-Log "" "INFO"
Write-Log "--- Phase 7: Verify New Location ---" "INFO"

foreach ($result in $moveResults) {
    if ($result.Status -eq "SUCCESS") {
        $task = Get-ScheduledTask -TaskName $result.TaskName -ErrorAction SilentlyContinue

        if ($task) {
            Write-Log "Task: $($result.TaskName)" "SUCCESS"
            Write-Log "  Path: $($task.TaskPath)" "INFO"
            Write-Log "  State: $($task.State)" "INFO"
            Write-Log "  Action: $($task.Actions[0].Execute) $($task.Actions[0].Arguments)" "INFO"

            if ($task.TaskPath -eq "\$TargetFolder\") {
                Write-Log "  VERIFIED: Task is in correct folder!" "SUCCESS"
            } else {
                Write-Log "  WARNING: Task is in wrong folder: $($task.TaskPath)" "WARNING"
            }
        } else {
            Write-Log "  ERROR: Task not found after registration!" "ERROR"
        }
    }

    Write-Log "" "INFO"
}

Write-Log "--- Phase 8: Start Moved Tasks ---" "INFO"

Write-Host ""
Write-Host "Do you want to start the moved tasks now? (yes/no)" -ForegroundColor Yellow
$startNow = Read-Host

if ($startNow -eq "yes") {
    foreach ($result in $moveResults) {
        if ($result.Status -eq "SUCCESS") {
            Write-Log "Starting task: $($result.TaskName)" "INFO"

            try {
                Start-ScheduledTask -TaskName $result.TaskName -ErrorAction Stop
                Start-Sleep -Seconds 2

                $taskState = (Get-ScheduledTask -TaskName $result.TaskName).State
                Write-Log "  Task started. State: $taskState" "SUCCESS"

            } catch {
                Write-Log "  ERROR: Failed to start task: $($_.Exception.Message)" "ERROR"
            }
        }
    }
} else {
    Write-Log "Tasks not started. You can start them manually from Task Scheduler." "INFO"
}

Write-Log "" "INFO"
Write-Log "=== Move Results Summary ===" "INFO"
Write-Log "" "INFO"

$successCount = 0
$failedCount = 0

foreach ($result in $moveResults) {
    $status = $result.Status
    $symbol = if ($status -eq "SUCCESS") { "[OK]" } else { "[FAIL]" }
    $level = if ($status -eq "SUCCESS") { "SUCCESS" } else { "ERROR" }

    Write-Log "$symbol $($result.TaskName): $status" $level

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
Write-Log "Total: $($moveResults.Count) tasks" "INFO"
Write-Log "Moved successfully: $successCount" "SUCCESS"
Write-Log "Failed: $failedCount" $(if ($failedCount -gt 0) { "ERROR" } else { "SUCCESS" })
Write-Log "" "INFO"
Write-Log "Log file saved to: $logFile" "INFO"
Write-Log "Backups saved to: $scriptDir\_Archiv\" "INFO"
Write-Log "" "INFO"
Write-Log "=== Move Operation Complete ===" "INFO"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  MOVE COMPLETE" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "Green" })
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Moved: $successCount / Failed: $failedCount" -ForegroundColor White
Write-Host ""
Write-Host "Tasks are now in folder: \$TargetFolder\" -ForegroundColor Green
Write-Host ""
Write-Host "To verify in Task Scheduler:" -ForegroundColor Cyan
Write-Host "1. Open Task Scheduler" -ForegroundColor White
Write-Host "2. Navigate to: Task Scheduler Library -> $TargetFolder" -ForegroundColor White
Write-Host "3. You should see both tasks there" -ForegroundColor White
Write-Host ""

# Exit with appropriate code
if ($failedCount -gt 0) {
    exit 1
} else {
    exit 0
}
