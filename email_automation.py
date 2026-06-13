#!/usr/bin/env python3
"""
Email Automation Script for LinkedIn Job Postings
Sends emails to job postings extracted from pipeline.md
"""

import re
import sys
import smtplib
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Optional
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('email_automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Email configuration (loaded from .env file)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")
NAME = os.getenv("NAME")
PHONE = os.getenv("PHONE")

# Dry run recipient
DRY_RUN_RECIPIENT = os.getenv("DRY_RUN_RECIPIENT")

# Resume attachments
REACT_RESUME = os.getenv("REACT_RESUME")
ANGULAR_RESUME = os.getenv("ANGULAR_RESUME")


def get_resume_attachment(keyword: str) -> Optional[str]:
    """
    Determine which resume to attach based on the job keyword using .env mappings.
    
    Args:
        keyword: Search keyword from the job posting
    
    Returns:
        Path to the resume file or None if no match
    """
    # Convert keyword to env variable format
    keyword_normalized = keyword.lower().replace(' ', '_')
    env_key = f"KEYWORD_{keyword_normalized.upper()}"
    
    # Get resume type from .env (0=React, 1=Angular)
    resume_type = os.getenv(env_key)
    
    if resume_type == '0':
        return REACT_RESUME
    elif resume_type == '1':
        return ANGULAR_RESUME
    
    return None


def update_pipeline_status(post_url: str, status: str, follow_up_count: int = 0) -> bool:
    """
    Update the email status in pipeline.md for a specific job posting.
    
    Args:
        post_url: The post URL to identify the job posting
        status: The new status ('Sent', 'Follow-up 1', 'Follow-up 2', etc.)
        follow_up_count: Number of follow-up emails sent
    
    Returns:
        True if update successful, False otherwise
    """
    try:
        with open('pipeline.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the post section with the matching URL and capture the intermediate lines
        pattern = rf'(- \*\*Post URL\*\*: {re.escape(post_url)}\n.*?\n)(- \*\*Status\*\*: `.*?` <!-- AUTOMATION_STATUS -->\n- \*\*Email Sent\*\*: `.*?` <!-- AUTOMATION_SENT -->)'
        
        if follow_up_count > 0:
            replacement = r'\1' + f'- **Status**: `{status}` <!-- AUTOMATION_STATUS -->\n- **Email Sent**: `Yes (Follow-up: {follow_up_count})` <!-- AUTOMATION_SENT -->'
        else:
            replacement = r'\1' + f'- **Status**: `{status}` <!-- AUTOMATION_STATUS -->\n- **Email Sent**: `Yes` <!-- AUTOMATION_SENT -->'
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if new_content == content:
            logger.warning(f"Could not find post with URL {post_url} to update status")
            return False
        
        with open('pipeline.md', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Updated pipeline.md status for {post_url}: {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating pipeline.md status: {e}")
        return False


def get_email_status(post_url: str) -> tuple:
    """
    Check the current email status for a job posting.
    
    Args:
        post_url: The post URL to check
    
    Returns:
        Tuple of (status, follow_up_count, email_sent)
    """
    try:
        with open('pipeline.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the post section with the matching URL
        pattern = rf'- \*\*Post URL\*\*: {re.escape(post_url)}\n- \*\*Status\*\*: `(.*?)` <!-- AUTOMATION_STATUS -->\n- \*\*Email Sent\*\*: `(.*?)` <!-- AUTOMATION_SENT -->'
        match = re.search(pattern, content)
        
        if match:
            status = match.group(1)
            email_sent = match.group(2)
            follow_up_count = 0
            
            if 'Follow-up' in email_sent:
                follow_match = re.search(r'Follow-up: (\d+)', email_sent)
                if follow_match:
                    follow_up_count = int(follow_match.group(1))
            
            return status, follow_up_count, email_sent
        
        return 'Pending', 0, 'No'
        
    except Exception as e:
        logger.error(f"Error checking email status: {e}")
        return 'Pending', 0, 'No'


def parse_pipeline_md(file_path: str) -> List[Dict]:
    """
    Parse pipeline.md file and extract job postings with emails.
    
    Returns:
        List of dictionaries containing job posting information
    """
    jobs = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by post sections using the correct separator
        posts = re.split(r'\n---\n\n### Post by', content)
        
        for post in posts[1:]:  # Skip first empty section
            job_data = {}
            
            # Extract author (first line after "Post by")
            lines = post.split('\n')
            if lines:
                job_data['author'] = lines[0].strip()
            
            # Extract author profile URL
            author_profile_match = re.search(r'- \*\*Author Profile\*\*: (.*?)\n', post)
            if author_profile_match:
                job_data['author_profile'] = author_profile_match.group(1).strip()
            
            # Extract post URL
            post_url_match = re.search(r'- \*\*Post URL\*\*: (.*?)\n', post)
            if post_url_match:
                job_data['post_url'] = post_url_match.group(1).strip()
            
            # Extract parsed emails
            emails_match = re.search(r'- \*\*Parsed Emails\*\*: `(.*?)`\n', post)
            if emails_match:
                emails_str = emails_match.group(1).strip()
                if emails_str and emails_str != 'None':
                    # Parse email list and clean up backticks
                    emails = [e.strip().replace('`', '') for e in emails_str.split(',')]
                    job_data['emails'] = emails
                else:
                    job_data['emails'] = []
            
            # Extract search keyword
            keyword_match = re.search(r'- \*\*Search Keyword\*\*: `(.*?)`\n', post)
            if keyword_match:
                job_data['keyword'] = keyword_match.group(1).strip()
            
            # Extract full post content
            content_start = post.find('**Full Post Content:**\n> ')
            if content_start != -1:
                content_start += len('**Full Post Content:**\n> ')
                content_end = post.find('\n---', content_start)
                if content_end != -1:
                    content = post[content_start:content_end].strip()
                else:
                    content = post[content_start:].strip()
                # Remove trailing "… more" if present
                if content.endswith('… more'):
                    content = content[:-7].strip()
                job_data['content'] = content
            else:
                # Debug: log the post content to understand the format
                logger.debug(f"Could not extract content for post. Post snippet: {post[:500]}")
                job_data['content'] = "Content extraction failed"
            
            # Only include jobs with emails
            if job_data.get('emails') and len(job_data['emails']) > 0:
                jobs.append(job_data)
        
        logger.info(f"Parsed {len(jobs)} job postings with emails from pipeline.md")
        return jobs
        
    except Exception as e:
        logger.error(f"Error parsing pipeline.md: {e}")
        return []


def generate_email_subject(job_data: Dict) -> str:
    """
    Generate a proper email subject for the job posting.
    """
    author = job_data.get('author', 'Unknown')
    keyword = job_data.get('keyword', 'Job Opportunity')
    
    # Extract job title from content if possible
    content = job_data.get('content', '')
    job_title = "Job Opportunity"
    
    # Try to extract job title from content
    title_patterns = [
        r'Hiring:\s*(.*?)\s*\|',
        r'Role:\s*(.*?)\s*\n',
        r'Position:\s*(.*?)\s*\n',
        r'(Senior|Junior|Lead|Principal)\s*(Developer|Engineer|Manager|Architect)'
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            job_title = match.group(1).strip()
            break
    
    # Exclude author from subject if unknown
    if author == "Unknown":
        subject = f"Application for {job_title} - {keyword}"
    else:
        subject = f"Application for {job_title} - {keyword} - {author}"
    return subject


def generate_email_body(job_data: Dict) -> str:
    """
    Generate a proper email body for the job posting.
    """
    author = job_data.get('author', 'Unknown')
    author_profile = job_data.get('author_profile', '')
    keyword = job_data.get('keyword', 'Job Opportunity')
    post_url = job_data.get('post_url', '')
    content = job_data.get('content', '')
    
    # Use generic greeting if author is unknown
    greeting = "Dear Hiring Team," if author == "Unknown" else f"Dear {author},"
    
    body = f"""{greeting}

I hope this email finds you well. I came across your job posting on LinkedIn and wanted to express my interest in the opportunity.

**Job Details:**
- Search Keyword: {keyword}
- Posted by: {author}
- LinkedIn Profile: {author_profile}
- Job Post URL: {post_url}

**Job Description:**
{content}

I am a front-end developer with 10+ years of experience and would like to apply for this position. I am confident that my expertise and background align well with the requirements of this role. Please let me know if you would like to review my resume or schedule a call to discuss further.

Best regards,
{NAME}
{PHONE}
{FROM_EMAIL}
"""
    
    return body


def send_email(to_email: str, subject: str, body: str, dry_run: bool = False, attachment_path: Optional[str] = None) -> bool:
    """
    Send email using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body
        dry_run: If True, print email details instead of sending
        attachment_path: Path to file to attach (optional)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if dry_run:
        logger.info(f"DRY RUN - Would send email to: {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body:\n{body}")
        if attachment_path:
            logger.info(f"Attachment: {attachment_path}")
        return True
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach body
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach file if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(attachment_path)}'
                )
                msg.attach(part)
            logger.info(f"Attached resume: {attachment_path}")
        elif attachment_path:
            logger.warning(f"Attachment file not found: {attachment_path}")
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to: {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False


def run_email_automation(dry_run: bool = False, limit: Optional[int] = None, follow_up: bool = False):
    """
    Run the email automation process.
    
    Args:
        dry_run: If True, send to DRY_RUN_RECIPIENT instead of actual emails
        limit: Maximum number of emails to send (None for all)
        follow_up: If True, send follow-up emails to already contacted jobs
    """
    # Parse pipeline.md
    jobs = parse_pipeline_md('pipeline.md')
    
    if not jobs:
        logger.warning("No job postings with emails found in pipeline.md")
        return
    
    # Apply limit if specified
    if limit:
        jobs = jobs[:limit]
        logger.info(f"Processing first {limit} job postings (dry run: {dry_run})")
    else:
        logger.info(f"Processing all {len(jobs)} job postings (dry run: {dry_run})")
    
    # Process each job
    success_count = 0
    failure_count = 0
    
    for i, job in enumerate(jobs, 1):
        logger.info(f"Processing job {i}/{len(jobs)}: {job.get('author', 'Unknown')}")
        
        # Check current email status
        post_url = job.get('post_url', '')
        current_status, follow_up_count, email_sent = get_email_status(post_url)
        
        # Determine if this is a follow-up (auto-switch if status is Sent)
        if email_sent == 'Yes':
            follow_up_count += 1
            new_status = f'Follow-up {follow_up_count}'
            logger.info(f"Auto-switching to follow-up mode (Status: {current_status})")
            logger.info(f"Sending follow-up email #{follow_up_count}")
        else:
            new_status = 'Sent'
            follow_up_count = 0
            logger.info(f"Sending initial email")
        
        # Generate email content
        subject = generate_email_subject(job)
        body = generate_email_body(job)
        
        # Modify subject for follow-ups
        if follow_up_count > 0:
            subject = f"Follow-up: {subject}"
        
        # Determine resume attachment based on keyword
        keyword = job.get('keyword', '')
        attachment_path = get_resume_attachment(keyword)
        
        # Determine recipient
        if dry_run:
            recipient = DRY_RUN_RECIPIENT
        else:
            # Send to all parsed emails for this job
            emails = job.get('emails', [])
            if not emails:
                logger.warning(f"No emails found for job {i}, skipping")
                continue
            
            # Send to first email only (can be modified to send to all)
            recipient = emails[0]
        
        # Send email with attachment
        if send_email(recipient, subject, body, dry_run=dry_run, attachment_path=attachment_path):
            success_count += 1
            # Update pipeline.md status only if not dry run
            if not dry_run:
                update_pipeline_status(post_url, new_status, follow_up_count)
        else:
            failure_count += 1
        
        # Add delay between emails to avoid rate limiting
        if not dry_run and i < len(jobs):
            import time
            time.sleep(2)
    
    logger.info(f"Email automation completed. Success: {success_count}, Failure: {failure_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Email Automation for LinkedIn Job Postings')
    parser.add_argument('--dry-run', action='store_true', help='Send to dry run recipient instead of actual emails')
    parser.add_argument('--limit', type=int, help='Limit number of emails to send')
    parser.add_argument('--follow-up', action='store_true', help='Send follow-up emails to already contacted jobs')
    
    args = parser.parse_args()
    
    logger.info("Starting email automation...")
    logger.info(f"Dry run mode: {args.dry_run}")
    logger.info(f"Follow-up mode: {args.follow_up}")
    logger.info(f"Limit: {args.limit if args.limit else 'No limit'}")
    
    run_email_automation(dry_run=args.dry_run, limit=args.limit, follow_up=args.follow_up)
