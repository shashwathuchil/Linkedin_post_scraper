#!/usr/bin/env python3
"""
LinkedIn Scraper using Playwright MCP Tools
This script is designed to be run interactively through the AI assistant with MCP tools.
It has improved data extraction logic compared to the original scraper.py.
"""

import os
import re
import time
import random
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Import utilities
from utils import extract_emails, clean_text, setup_logger

# Initialize logger
logger = setup_logger()

# Configuration
PIPELINE_FILE = "pipeline.md"
SCROLL_STEPS = 6
SCROLL_DELAY_MS = 2500

def load_keywords_from_env() -> list:
    """Load all search keywords from .env file."""
    load_dotenv()
    keywords = []
    
    for key, value in os.environ.items():
        if key.startswith('KEYWORD_'):
            keyword = key.replace('KEYWORD_', '').replace('_', ' ').title()
            keywords.append(keyword)
    
    keywords.sort()
    
    if not keywords:
        logger.warning("No KEYWORD_* found in .env file, using default keywords")
        return ["Hiring react", "Hiring angular", "Hiring ionic", "Hiring javascript"]
    
    logger.info(f"Loaded {len(keywords)} keywords from .env file: {keywords}")
    return keywords

def load_existing_urls(filepath: str) -> set:
    """Reads pipeline.md and extracts already scraped post URLs to avoid duplicates."""
    existing_urls = set()
    if not os.path.exists(filepath):
        return existing_urls
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        urls = re.findall(r'https://www\.linkedin\.com/feed/update/[^\s\)\`\]]+', content)
        for url in urls:
            clean_url = url.strip().strip(')').strip(']')
            existing_urls.add(clean_url)
            
        msg = f"Loaded {len(existing_urls)} existing post URLs from {filepath} to prevent duplicates."
        logger.info(msg)
    except Exception as e:
        msg = f"Error reading existing pipeline.md: {e}. Starting fresh."
        logger.error(msg)
        
    return existing_urls

def improved_extract_job_data(html_content: str) -> dict:
    """
    Improved data extraction from LinkedIn post HTML.
    Uses multiple strategies for better accuracy.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find job posts using componentkey attribute
    job_posts = soup.find_all('div', attrs={'componentkey': lambda x: x and 'FeedType_FLAGSHIP_SEARCH' in str(x)})
    
    results = []
    
    for job_post in job_posts:
        try:
            # Improved author extraction - try multiple selectors
            author = "Unknown"
            author_url = ""
            
            # Strategy 1: Look for author in span with specific class patterns
            author_p = job_post.find('p', class_=lambda x: x and '_893f12ae' in str(x))
            if author_p:
                author_span = author_p.find('span')
                if author_span:
                    author = author_span.get_text().strip()
            
            # Strategy 2: Extract from /in/ links
            if author == "Unknown":
                author_link = job_post.find('a', href=lambda x: x and '/in/' in str(x))
                if author_link:
                    author_elem = author_link.find('span')
                    if author_elem:
                        author = author_elem.get_text().strip()
                    author_url = author_link.get('href', '')
                    if author_url and not author_url.startswith('http'):
                        author_url = f"https://www.linkedin.com{author_url}"
            
            # Strategy 3: Look for profile links with /company/ or /in/
            if author == "Unknown":
                profile_links = job_post.find_all('a', href=lambda x: x and ('/in/' in x or '/company/' in x))
                for p_link in profile_links:
                    p_text = p_link.get_text().strip()
                    if p_text and len(p_text.split()) >= 2 and len(p_text) < 50:
                        clean_name = p_text.split('•')[0].strip()
                        if clean_name and not any(word in clean_name.lower() for word in ['hiring', 'looking', 'we are', 'role', 'position']):
                            author = clean_name
                            author_url = p_link.get('href', '')
                            if author_url and not author_url.startswith('http'):
                                author_url = f"https://www.linkedin.com{author_url}"
                            break
            
            # Improved job description extraction
            job_description = ""
            
            # Strategy 1: Look for componentkey with feed-commentary
            desc_elem = job_post.find('p', attrs={'componentkey': lambda x: x and 'feed-commentary' in str(x)})
            if desc_elem:
                job_description = desc_elem.get_text().strip()
            
            # Strategy 2: Look for expandable-text-box data-testid
            if not job_description:
                desc_elem = job_post.find('span', attrs={'data-testid': 'expandable-text-box'})
                if desc_elem:
                    job_description = desc_elem.get_text().strip()
            
            # Strategy 3: Look for any p element with substantial text
            if not job_description:
                for p in job_post.find_all('p'):
                    text = p.get_text().strip()
                    if len(text) > 50:
                        job_description = text
                        break
            
            # Strategy 4: Look for div with specific aria-label or data-attributes
            if not job_description:
                for div in job_post.find_all('div'):
                    aria_label = div.get('aria-label', '')
                    if aria_label and len(aria_label) > 50:
                        job_description = aria_label
                        break
            
            # Improved email extraction
            emails = []
            
            # Extract from mailto links
            mailto_links = job_post.find_all('a', attrs={'href': lambda x: x and 'mailto:' in str(x)})
            for link in mailto_links:
                email = link.get('href', '').replace('mailto:', '').strip()
                if email and email not in emails:
                    emails.append(email)
            
            # Extract from text using improved patterns
            if job_description:
                text_emails = extract_emails(job_description)
                for email in text_emails:
                    if email not in emails:
                        emails.append(email)
            
            # Improved post URL extraction
            post_url = ""
            
            # Strategy 1: Look for job links
            job_link = job_post.find('a', href=lambda x: x and 'linkedin.com/jobs/view' in str(x))
            if job_link:
                post_url = job_link.get('href', '').strip()
            
            # Strategy 2: Look for feed update links
            if not post_url:
                feed_link = job_post.find('a', href=lambda x: x and 'linkedin.com/feed/update' in str(x))
                if feed_link:
                    post_url = feed_link.get('href', '').strip()
            
            # Strategy 3: Look for any link with urn:li
            if not post_url:
                fallback_link = job_post.find('a', href=lambda x: x and 'urn:li:' in str(x))
                if fallback_link:
                    post_url = fallback_link.get('href', '').strip()
            
            # Improved job title extraction
            job_title = "Unknown Job"
            if job_description:
                # Look for specific job title patterns
                title_patterns = [
                    r'(Senior|Lead|Principal|Staff)?\s*(Front[- ]?End|Back[- ]?End|Full[- ]?Stack)?\s*(Software|Web)?\s*(Engineer|Developer)',
                    r'(React|Angular|Vue|Node\.js|Python|Java|\.NET)\s*(Developer|Engineer)',
                    r'(UI|UX)\s*(Designer|Developer|Engineer)',
                    r'(Product|Project)\s+Manager',
                    r'(Data|Machine Learning|AI)\s*(Scientist|Engineer)'
                ]
                
                for pattern in title_patterns:
                    match = re.search(pattern, job_description, re.IGNORECASE)
                    if match:
                        job_title = match.group(0)
                        break
                
                # Fallback to generic detection
                if job_title == "Unknown Job":
                    if 'Engineer' in job_description:
                        job_title = "Engineer"
                    elif 'Developer' in job_description:
                        job_title = "Developer"
                    elif 'Manager' in job_description:
                        job_title = "Manager"
            
            # Improved company name extraction
            company_name = "Unknown Company"
            if job_description:
                lines = job_description.split('\n')
                if lines:
                    first_line = lines[0].strip()
                    # Company name is often the first word or phrase before "is hiring"
                    if 'is hiring' in first_line:
                        company_name = first_line.split('is hiring')[0].strip()
                    elif 'hiring' in first_line.lower():
                        company_name = first_line.split('hiring')[0].strip()
                    elif first_line and len(first_line.split()) <= 3:
                        company_name = first_line
            
            # Improved location extraction
            location = "Unknown Location"
            if job_description:
                location_patterns = [
                    r'(Remote|Hybrid|On[- ]?site)',
                    r'(Bangalore|Bengaluru|Mumbai|Delhi|Pune|Chennai|Hyderabad)',
                    r'(India|USA|UK|Canada|Australia)',
                    r'(California|New York|Texas|Washington)'
                ]
                
                for pattern in location_patterns:
                    match = re.search(pattern, job_description, re.IGNORECASE)
                    if match:
                        location = match.group(0)
                        break
            
            # Only add if we have meaningful data
            if job_description or post_url or emails:
                results.append({
                    "status": "new",
                    "author": author,
                    "author_url": author_url,
                    "post_url": post_url,
                    "text": job_description,
                    "emails": emails,
                    "date": "Recent",
                    "job_title": job_title,
                    "company": company_name,
                    "location": location
                })
                
        except Exception as e:
            logger.warning(f"Error extracting job data from post: {e}")
            continue
    
    return results

def append_to_pipeline(post_data: dict, keyword: str):
    """Appends a successfully scraped post to pipeline.md."""
    logger.info(f"Writing post to pipeline.md - Author: '{post_data['author']}' | Emails: {post_data['emails']} | URL: {post_data['post_url']}")
    file_exists = os.path.exists(PIPELINE_FILE)
    
    with open(PIPELINE_FILE, 'a', encoding='utf-8') as f:
        if not file_exists:
            f.write("# LinkedIn Lead Automation Pipeline\n\n")
            f.write("This file is automatically updated by the LinkedIn post scraper. It is designed to feed into an automated email system. Change status from `Pending` to `Emailed` or `Skipped` once processed.\n\n")
            f.write("---\n\n")
            
        f.write(f"### Post by {post_data['author']}\n")
        if post_data['author_url']:
            f.write(f"- **Author Profile**: {post_data['author_url']}\n")
        f.write(f"- **Post URL**: {post_data['post_url']}\n")
        
        emails = post_data['emails']
        if emails:
            emails_str = ", ".join([f"`{e}`" for e in emails])
            status_str = "Pending"
        else:
            emails_str = "`None`"
            status_str = "Skipped"
            
        f.write(f"- **Parsed Emails**: {emails_str}\n")
        f.write(f"- **Search Keyword**: `{keyword}`\n")
        f.write(f"- **Scraped Date/Relative Time**: `{post_data['date']}`\n")
        f.write(f"- **Scraping Timestamp**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n")
        f.write(f"- **Status**: `{status_str}` <!-- AUTOMATION_STATUS -->\n")
        f.write("- **Email Sent**: `No` <!-- AUTOMATION_SENT -->\n")
        f.write("\n**Full Post Content:**\n")
        
        quoted_text = "\n".join([f"> {line}" for line in post_data['text'].split('\n') if line])
        f.write(f"{quoted_text}\n\n")
        f.write("---\n\n")

def initialize_pipeline_file():
    """Creates pipeline.md with headers if it does not already exist."""
    if not os.path.exists(PIPELINE_FILE):
        with open(PIPELINE_FILE, 'w', encoding='utf-8') as f:
            f.write("# LinkedIn Lead Automation Pipeline\n\n")
            f.write("This file is automatically updated by the LinkedIn post scraper. It is designed to feed into an automated email system. Change status from `Pending` to `Emailed` or `Skipped` once processed.\n\n")
            f.write("---\n\n")
        logger.info(f"Initialized new empty pipeline file at {PIPELINE_FILE}")

def main():
    """
    Main function to orchestrate the scraping process.
    This function is designed to be called by the AI assistant using MCP tools.
    The AI assistant will handle the browser automation using MCP Playwright tools.
    """
    logger.info("Initializing LinkedIn Content Scraper with MCP...")
    
    # Load keywords from .env file
    keywords = load_keywords_from_env()
    
    # Ensure pipeline file exists
    initialize_pipeline_file()
    
    # Load already scraped URLs to avoid duplicating entries
    existing_urls = load_existing_urls(PIPELINE_FILE)
    
    print(f"Loaded {len(keywords)} keywords from .env file")
    print(f"Loaded {len(existing_urls)} existing post URLs from pipeline.md")
    print("\nReady to start scraping. The AI assistant will now use MCP Playwright tools to:")
    print("1. Navigate to LinkedIn search results for each keyword")
    print("2. Scroll to load more posts")
    print("3. Expand truncated posts")
    print("4. Extract post data with improved logic")
    print("5. Save results to pipeline.md")
    print("\nPlease proceed with the MCP browser automation.")

if __name__ == "__main__":
    main()
