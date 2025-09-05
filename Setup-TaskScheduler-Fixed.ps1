# PowerShell Script to Setup Task Scheduler for Status Monitoring System
# Run as Administrator

param(
    [string]$ServiceAccount = "Service",
    [string]$BasePath = "D:\Dataserver\_Batchprozesse\status"
)

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as Administrator. Please restart PowerShell as Administrator and try again."
    exit 1
}

Write-Host "Setting up Task Scheduler tasks for Status Monitoring System..." -ForegroundColor Green
Write-Host "Service Account: $ServiceAccount" -ForegroundColor Yellow
Write-Host "Base Path: $BasePath" -ForegroundColor Yellow

# Import Task Scheduler module
Import-Module ScheduledTasks

try {
    # Task 1: Flask Web Application
    Write-Host "`nCreating Task 1: Status Web App..." -ForegroundColor Cyan
    
    $Action1 = New-ScheduledTaskAction -Execute "$BasePath\start_app.bat" -WorkingDirectory $BasePath
    $Trigger1 = New-ScheduledTaskTrigger -AtStartup
    $Principal1 = New-ScheduledTaskPrincipal -UserId $ServiceAccount -LogonType ServiceAccount -RunLevel Highest
    $Settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -DontStopOnIdleEnd -RestartOnIdle -ExecutionTimeLimit (New-TimeSpan -Hours 0)
    
    $Task1 = New-ScheduledTask -Action $Action1 -Trigger $Trigger1 -Principal $Principal1 -Settings $Settings1 -Description "Flask web application for stock monitoring dashboard"
    
    Register-ScheduledTask -TaskName "Status Web App" -TaskPath "\AHSkripts\" -InputObject $Task1 -Force
    Write-Host "Task 1 created successfully" -ForegroundColor Green

    # Task 2: Stock Monitoring Service
    Write-Host "`nCreating Task 2: Stock Monitoring Service..." -ForegroundColor Cyan
    
    $Action2 = New-ScheduledTaskAction -Execute "$BasePath\start_status.bat" -WorkingDirectory $BasePath
    $Trigger2 = New-ScheduledTaskTrigger -AtStartup
    $Trigger2.Delay = "PT2M"  # 2 minute delay
    $Principal2 = New-ScheduledTaskPrincipal -UserId $ServiceAccount -LogonType ServiceAccount -RunLevel Highest
    $Settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -DontStopOnIdleEnd -RestartOnIdle -ExecutionTimeLimit (New-TimeSpan -Hours 0)
    
    $Task2 = New-ScheduledTask -Action $Action2 -Trigger $Trigger2 -Principal $Principal2 -Settings $Settings2 -Description "Stock price monitoring and portfolio tracking"
    
    Register-ScheduledTask -TaskName "Stock Monitoring Service" -TaskPath "\AHSkripts\" -InputObject $Task2 -Force
    Write-Host "Task 2 created successfully" -ForegroundColor Green

    # Task 3: DSL Speedtest Monitoring
    Write-Host "`nCreating Task 3: DSL Speedtest Monitoring..." -ForegroundColor Cyan
    
    $Action3 = New-ScheduledTaskAction -Execute "$BasePath\start_status_dsl.bat" -WorkingDirectory $BasePath
    $Trigger3 = New-ScheduledTaskTrigger -AtStartup
    $Trigger3.Delay = "PT3M"  # 3 minute delay
    $Principal3 = New-ScheduledTaskPrincipal -UserId $ServiceAccount -LogonType ServiceAccount -RunLevel Highest
    $Settings3 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -DontStopOnIdleEnd -RestartOnIdle -ExecutionTimeLimit (New-TimeSpan -Hours 0)
    
    $Task3 = New-ScheduledTask -Action $Action3 -Trigger $Trigger3 -Principal $Principal3 -Settings $Settings3 -Description "DSL speedtest monitoring and data collection"
    
    Register-ScheduledTask -TaskName "DSL Speedtest Monitoring" -TaskPath "\AHSkripts\" -InputObject $Task3 -Force
    Write-Host "Task 3 created successfully" -ForegroundColor Green

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "SUCCESS: All tasks have been created successfully!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    
    Write-Host "`nCreated Tasks:" -ForegroundColor Yellow
    Write-Host "1. Status Web App - Starts immediately at system startup" -ForegroundColor White
    Write-Host "2. Stock Monitoring Service - Starts 2 minutes after startup" -ForegroundColor White  
    Write-Host "3. DSL Speedtest Monitoring - Starts 3 minutes after startup" -ForegroundColor White

    # Display tasks
    Write-Host "`nVerifying created tasks..." -ForegroundColor Cyan
    Get-ScheduledTask -TaskPath "\AHSkripts\" | Where-Object {$_.TaskName -in @("Status Web App", "Stock Monitoring Service", "DSL Speedtest Monitoring")} | Select-Object TaskName, State | Format-Table -AutoSize

    Write-Host "`nNext Steps:" -ForegroundColor Yellow
    Write-Host "1. Verify Service account has proper permissions on $BasePath" -ForegroundColor White
    Write-Host "2. Ensure Service account has 'Log on as a service' right" -ForegroundColor White
    Write-Host "3. Test tasks by right-clicking each task in Task Scheduler and selecting 'Run'" -ForegroundColor White
    Write-Host "4. Open Windows Firewall port 5000 for Flask application" -ForegroundColor White
    Write-Host "5. Reboot server to test automatic startup" -ForegroundColor White

}
catch {
    Write-Error "Failed to create tasks: $_"
    Write-Host "`nPossible solutions:" -ForegroundColor Yellow
    Write-Host "1. Ensure you are running as Administrator" -ForegroundColor White
    Write-Host "2. Verify the Service account '$ServiceAccount' exists" -ForegroundColor White
    Write-Host "3. Check that the path '$BasePath' exists" -ForegroundColor White
    Write-Host "4. Ensure batch files exist in the specified path" -ForegroundColor White
    exit 1
}

Write-Host "`nTask setup completed successfully!" -ForegroundColor Green
Read-Host "Press Enter to exit"