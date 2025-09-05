# Windows Server Deployment Guide

This document describes how to deploy the Status monitoring system on a Windows Server using Task Scheduler to run services automatically on system startup.

## Overview

The deployment consists of 3 automated services:
1. **Flask Web App** (`app.py`) - Web dashboard for monitoring
2. **Stock Monitor** (`status.py`) - Stock price monitoring and portfolio tracking
3. **DSL Speedtest** (`status_dsl.py`) - Internet speed monitoring and data collection

## Prerequisites

- Windows Server with Administrator access
- Python 3.x installed and accessible in PATH
- Git repository cloned to `D:\Dataserver\_Batchprozesse\status`
- Service account configured on the server
- Required Python packages installed (`pip install -r requirements.txt`)

## Step 1: Repository Setup

1. **Clone Repository on Server:**
   ```cmd
   cd D:\Dataserver\_Batchprozesse
   git clone [repository-url] status
   cd status
   ```

2. **Pull Latest Updates:**
   ```cmd
   git pull origin main
   ```

3. **Install Dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```

4. **Copy Batch Files:**
   Copy the following batch files from your local repository to the server:
   - `start_app.bat`
   - `start_status.bat` 
   - `start_status_dsl.bat`

## Step 2: Service Account Permissions

### Grant Folder Permissions
1. Right-click `D:\Dataserver\_Batchprozesse\status` → **Properties** → **Security**
2. Click **"Edit..."** → **"Add..."**
3. Enter `Service` → **"Check Names"** → **OK**
4. Select `Service` user → Grant permissions:
   - ☑️ **Full control** (recommended)
   - Or minimum: Read & execute, Write, Modify
5. Click **"Advanced"** → Check **"Replace child object permissions"**
6. **Apply** to all subfolders and files

### Grant "Log on as Service" Right
1. Press `Win + R`, type `secpol.msc`, press **Enter**
2. Navigate: **Security Settings** → **Local Policies** → **User Rights Assignment**
3. Double-click **"Log on as a service"**
4. Click **"Add User or Group..."** → Enter `Service` → **OK**
5. **Apply** changes

### Network Share Access (if needed)
- Ensure `Service` account can access external paths:
  - `\\WIN-H7BKO5H0RMC\Dataserver\...`
- May require domain credentials or UNC path configuration

## Step 3: Task Scheduler Configuration

### Open Task Scheduler
1. Press `Win + R`, type `taskschd.msc`, press **Enter**
2. Run as **Administrator**
3. Right-click **"Task Scheduler Library"** → **"Create Task..."**

### Task 1: Flask Web Application

**General Tab:**
- **Name:** `Status Web App`
- **Description:** `Flask web application for stock monitoring dashboard`
- **User account:** `Service`
- ☑️ **Run whether user is logged on or not**
- ☑️ **Run with highest privileges**
- **Configure for:** Windows Server (your version)

**Triggers Tab:**
- Click **"New..."** → **"At startup"**
- ☑️ **Enabled**

**Actions Tab:**
- Click **"New..."** → **"Start a program"**
- **Program/script:** `D:\Dataserver\_Batchprozesse\status\start_app.bat`
- **Start in:** `D:\Dataserver\_Batchprozesse\status`

**Conditions Tab:**
- ☐ Start the task only if the computer is on AC power (uncheck this)
- ☑️ Wake the computer to run this task

**Settings Tab:**
- ☑️ Allow task to be run on demand
- ☑️ If the running task does not end when requested, force it to stop
- **If the task is already running:** Do not start a new instance

### Task 2: Stock Monitoring Service

**General Tab:**
- **Name:** `Stock Monitoring Service`
- **Description:** `Stock price monitoring and portfolio tracking`
- **User account:** `Service`
- ☑️ **Run whether user is logged on or not**
- ☑️ **Run with highest privileges**

**Triggers Tab:**
- Click **"New..."** → **"At startup"**
- **Delay task for:** `2 minutes` (wait for network initialization)
- ☑️ **Enabled**

**Actions Tab:**
- Click **"New..."** → **"Start a program"**
- **Program/script:** `D:\Dataserver\_Batchprozesse\status\start_status.bat`
- **Start in:** `D:\Dataserver\_Batchprozesse\status`

**Conditions & Settings:** Same as Task 1

### Task 3: DSL Speedtest Monitoring

**General Tab:**
- **Name:** `DSL Speedtest Monitoring`
- **Description:** `DSL speedtest monitoring and data collection`
- **User account:** `Service`
- ☑️ **Run whether user is logged on or not**
- ☑️ **Run with highest privileges**

**Triggers Tab:**
- Click **"New..."** → **"At startup"**
- **Delay task for:** `3 minutes` (wait for other services)
- ☑️ **Enabled**

**Actions Tab:**
- Click **"New..."** → **"Start a program"**
- **Program/script:** `D:\Dataserver\_Batchprozesse\status\start_status_dsl.bat`
- **Start in:** `D:\Dataserver\_Batchprozesse\status`

**Conditions & Settings:** Same as Task 1

## Step 4: Windows Firewall Configuration

### Open Port 5000 for Flask Application
1. Open **Windows Defender Firewall with Advanced Security**
2. Click **"Inbound Rules"** → **"New Rule..."**
3. **Rule Type:** Port
4. **Protocol:** TCP, **Specific local ports:** 5000
5. **Action:** Allow the connection
6. **Profile:** Apply to Domain, Private, and Public
7. **Name:** `Flask Status Dashboard`

## Step 5: Testing and Verification

### Test Individual Tasks
1. In Task Scheduler, right-click each task → **"Run"**
2. Check **Task History** for any errors
3. Verify processes are running in **Task Manager**

### Verify Services
1. **Flask Web App:** Navigate to `http://[server-ip]:5000`
2. **Stock Monitor:** Check log files in status directory
3. **DSL Speedtest:** Monitor `speedtest.json` updates every 60 seconds

### Check Log Files
Monitor these log files for proper operation:
- `status.log` - Stock monitoring logs
- `status_dsl.log` - DSL speedtest logs
- Windows Event Viewer → Windows Logs → System (for Task Scheduler events)

## Step 6: Maintenance and Monitoring

### Regular Tasks
- **Monitor disk space** (Parquet and log files grow over time)
- **Check task history** for failures
- **Update repository** periodically with `git pull`
- **Restart services** if needed via Task Scheduler

### Troubleshooting
- **Tasks not starting:** Check Service account permissions
- **Network errors:** Verify external file access and internet connectivity
- **Python errors:** Ensure all dependencies are installed for Service account
- **Port conflicts:** Verify no other applications use port 5000

### Data Files Locations
- **Stock data:** `prices.parquet`
- **DSL speedtest data:** `speedtest_data.parquet`
- **Web interface data:** `static/depotdaten.json`, `static/speedtest.json`
- **Configuration:** `status.ini`, `status_dsl.ini`

## System Requirements

- **CPU:** Minimal (services are lightweight)
- **RAM:** 512MB+ available
- **Disk:** 10GB+ free space (for data accumulation)
- **Network:** Stable internet connection for price/speedtest APIs
- **Python:** Version 3.8+

## Service Startup Order

1. **Flask Web App** - Immediate startup (0 minutes delay)
2. **Stock Monitor** - 2 minutes delay (wait for network)
3. **DSL Speedtest** - 3 minutes delay (prevent resource conflicts)

This staggered approach ensures reliable startup and prevents conflicts during server boot.

## Security Considerations

- Service account has minimal required permissions
- Web dashboard only accessible on port 5000
- No sensitive data exposed in configuration files
- Log files contain no credentials or personal information
- External file access limited to specified network paths

## Support and Updates

- **Log locations:** Check service-specific log files for errors
- **Updates:** Use `git pull` to get latest code changes
- **Configuration changes:** Restart affected tasks after INI file updates
- **Performance monitoring:** Use DSL Speedtest Viewer (`python dsl_speedtest_viewer.py`) for data analysis