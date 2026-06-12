---
description: How to automate and run the LinkedIn Content Scraper autonomously
---

This workflow provides step-by-step instructions on setting up, running, and maintaining the LinkedIn Content Post Lead Scraper completely autonomously in the background on your macOS environment.

### Prerequisites

Ensure you have Google Chrome installed on your Mac, as the scraper utilizes Chrome's active profile session.

---

### Step 1: Install Dependencies

Set up your Python workspace and install required packages.

// turbo
```bash
pip install -r requirements.txt && playwright install chromium
```

---

### Step 2: Open Google Chrome Debugging Instance (Headless or Headed)

The runner (`runner.py`) handles this automatically. If you wish to run it manually or headless:

* **Headed (First-time setup / Logging in)**:
  ```bash
  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="/path/to/project/chrome_profile" --no-first-run
  ```
  *Make sure to log in to LinkedIn once in the window that pops up. It will persist your login session in the `chrome_profile` directory.*

---

### Step 3: Run the Scraper Autonomously

To run the lead automation pipeline as a continuous background daemon, you have two primary options:

#### Option A: Running in continuous schedule mode with nohup (Recommended)
This launches the runner in daemon mode, scraping your keywords every 12 hours, automatically checking Chrome's port state, and writing to logs.

```bash
nohup python3 runner.py --interval 12.0 > runner.out 2>&1 &
```
*To verify that the daemon is running in the background:*
```bash
ps aux | grep runner.py
```

#### Option B: Automated scheduling via macOS launchd (System Agent)
Create a launch daemon plist to execute the scraper autonomously. This survives system restarts and executes silently.

1. Create a plist file `com.user.linkedinscraper.plist` in `~/Library/LaunchAgents/` with:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.linkedinscraper</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/project/runner.py</string>
    </array>
    <key>StartInterval</key>
    <integer>43200</integer> <!-- 12 Hours in seconds -->
    <key>WorkingDirectory</key>
    <string>/path/to/project</string>
    <key>StandardOutPath</key>
    <string>/path/to/project/launcher_out.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/project/launcher_err.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

2. Load and activate the autonomous launch agent:
```bash
launchctl load ~/Library/LaunchAgents/com.user.linkedinscraper.plist
```

---

### Step 4: Monitor Autonomous Execution

Keep track of lead collection and application state:

* **Watch scraping pipeline updates in real time**:
  ```bash
  tail -f pipeline.md
  ```
* **Watch system execution logs**:
  ```bash
  tail -f scraper.log
  ```
