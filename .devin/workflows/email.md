---
description: Email automation for LinkedIn job postings
---

# Email Automation Workflow

This workflow automates sending emails to job postings extracted from `pipeline.md`.

## Prerequisites

1. **Configure SMTP Settings**: Update the email configuration in `email_automation.py`:
   - `SMTP_USERNAME`: Your email address
   - `SMTP_PASSWORD`: Your app password (not regular password)
   - `FROM_EMAIL`: Your email address

2. **Get Gmail App Password** (if using Gmail):
   - Go to Google Account settings
   - Enable 2-factor authentication
   - Generate an app password for email access
   - Use this app password in the script

## Step 1: Update Email Configuration

// turbo
```bash
# Configure SMTP settings in .env file:
# SMTP_USERNAME=your_email@gmail.com
# SMTP_PASSWORD=your_app_password
# FROM_EMAIL=your_email@gmail.com
# NAME=Your Name
# PHONE=Your Phone Number
```

## Step 2: Dry Run Test

Test the email automation by sending one email to the dry run recipient (configured in .env as DRY_RUN_RECIPIENT):

```bash
python3 email_automation.py --dry-run --limit 1
```

This will:
- Parse the first job posting from `pipeline.md`
- Generate a proper email subject and body
- Print the email details to the console (not actually send)
- Attach appropriate resume based on job keyword
- Send to the dry run recipient instead of the actual parsed email

## Step 3: Production Run

After verifying the dry run, send emails to all job postings:

```bash
python3 email_automation.py
```

This will:
- Parse all job postings from `pipeline.md`
- Send emails to the actual parsed email addresses
- Attach appropriate resume (React for React jobs, Angular for Angular jobs)
- Update status in `pipeline.md` to track sent emails
- Add a 2-second delay between emails to avoid rate limiting

## Optional: Limit Number of Emails

To send emails to a specific number of job postings:

```bash
python3 email_automation.py --limit 5
```

## Optional: Follow-up Mode

Send follow-up emails to jobs that have already been contacted:

```bash
python3 email_automation.py --follow-up
```

This will:
- Send follow-up emails to jobs with status "Sent" or previous follow-ups
- Increment follow-up counter in `pipeline.md`
- Add "Follow-up:" prefix to email subject
- Track follow-up count in email status

## Command-Line Options

- `--dry-run`: Test without sending actual emails
- `--limit N`: Send only N emails
- `--follow-up`: Send follow-up emails to already contacted jobs

## Monitoring

Check the email automation log for details:

```bash
tail -f email_automation.log
```

## Email Content

The automation generates:
- **Subject**: Includes job title, search keyword, and author name (excludes author if unknown)
- **Body**: Includes job details, author information, job description, and call to action
- **Attachments**: Automatically attaches appropriate resume based on job keyword (configured in .env as REACT_RESUME and ANGULAR_RESUME)
- **Footer**: Includes name, phone, and email from .env file

## Status Tracking

The automation updates `pipeline.md` to track email status:
- **Initial email**: Status = "Sent", Email Sent = "Yes"
- **Follow-up emails**: Status = "Follow-up 1", Email Sent = "Yes (Follow-up: 1)"
- **Auto-switch**: When status is "Sent", the system automatically switches to follow-up mode for subsequent runs
- The `--follow-up` flag is optional - the system auto-switches when it detects already-sent jobs

## Safety Features

- **Dry Run Mode**: Test without sending actual emails
- **Rate Limiting**: 2-second delay between emails
- **Error Handling**: Logs failures and continues with remaining emails
- **Email Validation**: Only processes job postings with valid emails
- **Status Tracking**: Prevents duplicate emails to same job postings
- **Email Cleaning**: Removes markdown backticks from email addresses
