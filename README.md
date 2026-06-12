# LinkedIn Content Lead Scraper & Automation Pipeline

This project is a high-reliability Python scraper built to extract recruitment leads (specifically React, Angular, Ionic, and JavaScript hiring posts) from LinkedIn. It runs directly through your active Google Chrome browser session, bypassing anti-bot measures, Captchas, and complex login flows.

All scraped leads containing valid or obfuscated emails are saved in a structured, deduplicated Markdown pipeline (`pipeline.md`), ready for future automated email outreach.

---

## 🚀 Key Features

* **Authenticated Browser Session Integration**: Connects to your actual Google Chrome browser using Chrome DevTools Protocol (CDP) on port `9222`. No credentials, cookies, or secrets are stored in code.
* **Intelligent Email Parser**: Automatically extracts standard emails and bypasses obfuscation methods e.g., `user [at] gmail [dot] com`, `user(at)gmail.co.uk`, and `user at domain.com`.
* **Truncated Post Expansion**: Automatically clicks "...see more" buttons to load the full body text of LinkedIn posts before parsing, ensuring no contact info is missed.
* **Lead Deduplication**: Reads the existing `pipeline.md` file before running and automatically skips already scraped posts. You can run this daily without cluttering your pipeline or sending double emails.
* **Email Automation Ready**: Each lead is logged with metadata and status flags (`Status: Pending`, `Email Sent: No`) designed to be consumed by an automated mailing script.

---

## 🛠️ Setup Instructions

### 1. Install Dependencies

Install the required Python packages and configure Playwright:

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Launch Google Chrome in Remote Debugging Mode

Close all active Google Chrome windows first (or use a separate user-data profile). Open your macOS Terminal and execute the following command:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

This launches a fully functional Chrome window with developer hooks opened on port `9222`.

### 3. Log Into LinkedIn

In the Chrome browser window that just opened, navigate to [LinkedIn](https://www.linkedin.com) and log in if you aren't already. This session will be used by the scraper.

---

## 💻 Running and Maintaining the Scraper

There are two ways to run the scraper:
1. **Using the Runner (`runner.py`) [RECOMMENDED]**: Handles auto-launching Chrome and persistent logging.
2. **Direct Execution (`scraper.py`)**: Runs on-demand assuming you already started Chrome manually.

### Option 1: Managed Execution with `runner.py` (Recommended)

The runner automate Chrome process health checks, manages dedicated profiles, logs script events persistently, and supports continuous loop scheduling.

#### Run On-Demand (Single Scrape)
```bash
python3 runner.py
```
*If Chrome is not running on port 9222, this script will launch it in a separate profile, prompt you to log in to LinkedIn (only once), and then run the scraper.*

#### Run on a Continuous Schedule (Daemon Mode)
To run the scraper automatically in the background every 12 hours (it will maintain Chrome connection and log runs):
```bash
python3 runner.py --interval 12.0
```
*(You can run this in a `screen`, `tmux`, or in the background to maintain a 24/7 lead collection loop).*

---

### Option 2: Direct Manual Run with `scraper.py`

If you prefer starting Chrome manually yourself:
1. Manually launch Google Chrome on port 9222.
2. Execute the scraper:
   ```bash
   python3 scraper.py
   ```

---

## 🪵 Persistent Application Logs

A unified logging system maintains records of all operations (scrapes, lead captures, Chrome state changes, session failures, etc.). 

- **Log File**: `scraper.log` (created automatically in the root directory).
- **Log Rotation**: Automatically rotates logs when they reach **5MB**, keeping up to **3 archive backups** (`scraper.log.1`, `scraper.log.2`, etc.) to prevent disk bloat.
- **Log Format**: `[TIMESTAMP] [LOG_LEVEL] [FILE_NAME:LINE_NUMBER]: MSG`

Example Log Entries:
```text
[2026-06-12 14:45:01,234] [INFO] [runner.py:112]: Chrome successfully launched and listening on port 9222.
[2026-06-12 14:45:05,567] [INFO] [scraper.py:49]: Loaded 14 existing post URLs from pipeline.md to prevent duplicates.
[2026-06-12 14:45:12,123] [INFO] [scraper.py:251]: Navigating to search URL: https://www.linkedin.com/search/results/content/?keywords=Hiring%20react...
[2026-06-12 14:45:45,999] [INFO] [scraper.py:175]: Writing lead to pipeline.md - Author: 'Jane Doe' | Emails: ['jane.doe@techcorp.com'] | URL: https://www.linkedin.com/feed/update/urn:li:activity:7123456789012345678/
```

---

## 📁 Output Pipeline Schema (`pipeline.md`)

The scraper appends lead cards to `pipeline.md`. It uses a consistent markdown layout with built-in HTML comment hooks for future email automation parsers:

```markdown
### Post by [John Doe](https://www.linkedin.com/in/johndoe/)
- **Author Profile**: https://www.linkedin.com/in/johndoe/
- **Post URL**: https://www.linkedin.com/feed/update/urn:li:activity:7123456789012345678/
- **Parsed Emails**: `john.doe@gmail.com`
- **Search Keyword**: `Hiring react`
- **Scraped Date/Relative Time**: `1d ago`
- **Scraping Timestamp**: `2026-06-12 14:40:00`
- **Status**: `Pending` <!-- AUTOMATION_STATUS -->
- **Email Sent**: `No` <!-- AUTOMATION_SENT -->

**Full Post Content:**
> We are looking for an experienced React Developer to join our team!
> Reach out to john.doe@gmail.com with your resume.

---
```

### Future Email Automation Integration:
A downstream automation script can read `pipeline.md` and process it easily:
1. Search for items containing `- **Status**: \`Pending\`` and `- **Parsed Emails**: \`<email>\``.
2. Send the email using your preferred mailing framework (like Python's `smtplib`, Resend, or SendGrid).
3. Update the markdown file lines to:
   * `- **Status**: \`Emailed\`` (or `Skipped`/`Interested`/`Replied`)
   * `- **Email Sent**: \`Yes\``

---

## ⚙️ Configuration & Customization

You can open `scraper.py` and adjust the following parameters near the top of the file:

* `DEFAULT_KEYWORDS`: List of queries you want to search.
* `SCROLL_STEPS`: Number of scroll iterations to load older posts (increase for more posts per keyword).
* `SCROLL_DELAY_MS`: Time (in milliseconds) to wait for lazy-loading elements.
