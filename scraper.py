import os
import re
import sys
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

# Import utilities
from utils import extract_emails, clean_text, setup_logger

# Initialize logger and rich console
logger = setup_logger()
console = Console()

# Configuration
CHROME_CDP_URL = "http://localhost:9222"
PIPELINE_FILE = "pipeline.md"
SCROLL_STEPS = 6  # Number of scrolls per keyword to load enough posts
SCROLL_DELAY_MS = 2500  # Milliseconds to wait after each scroll

def load_keywords_from_env() -> list:
    """Load all search keywords from .env file."""
    load_dotenv()
    keywords = []
    
    # Find all environment variables starting with KEYWORD_
    for key, value in os.environ.items():
        if key.startswith('KEYWORD_'):
            # Convert KEYWORD_HIRING_REACT to "Hiring react"
            keyword = key.replace('KEYWORD_', '').replace('_', ' ').title()
            keywords.append(keyword)
    
    # Sort keywords for consistent ordering
    keywords.sort()
    
    if not keywords:
        logger.warning("No KEYWORD_* found in .env file, using default keywords")
        return [
            "Hiring react",
            "Hiring angular",
            "Hiring ionic",
            "Hiring javascript"
        ]
    
    logger.info(f"Loaded {len(keywords)} keywords from .env file: {keywords}")
    return keywords

def load_existing_urls(filepath: str) -> set:
    """Reads pipeline.md if it exists and extracts already scraped post URLs/URNs to avoid duplicates."""
    existing_urls = set()
    if not os.path.exists(filepath):
        return existing_urls
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Regex to find LinkedIn update/post URLs in the file
        # Matches: https://www.linkedin.com/feed/update/urn:li:...
        urls = re.findall(r'https://www\.linkedin\.com/feed/update/[^\s\)\`\]]+', content)
        for url in urls:
            # Clean trailing punctuation
            clean_url = url.strip().strip(')').strip(']')
            existing_urls.add(clean_url)
            
        msg = f"Loaded {len(existing_urls)} existing post URLs from {filepath} to prevent duplicates."
        logger.info(msg)
        console.print(f"[yellow]{msg}[/yellow]")
    except Exception as e:
        msg = f"Error reading existing pipeline.md: {e}. Starting fresh."
        logger.error(msg)
        console.print(f"[red]{msg}[/red]")
        
    return existing_urls

def extract_urn_from_html(element_html: str) -> str:
    """Tries to find URN inside the elements HTML."""
    # Common URN formats: urn:li:activity:XXXX or urn:li:ugcPost:XXXX or urn:li:share:XXXX
    urn_match = re.search(r'urn:li:(?:activity|ugcPost|share|update):\d+', element_html)
    if urn_match:
        return urn_match.group(0)
    return ""

def extract_job_data(job_post) -> dict:
    """
    Extracts job-specific data from a LinkedIn job post HTML element.
    Returns a dict with job title, company, location, email, post_url, etc.
    """
    try:
        # Extract job description using multiple strategies
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
                if len(text) > 50:  # Only consider substantial text
                    job_description = text
                    break
        
        # Extract email from mailto links with specific class pattern
        emails = []
        mailto_links = job_post.find_all('a', attrs={'href': lambda x: x and 'mailto:' in str(x)})
        for link in mailto_links:
            email = link.get('href', '').replace('mailto:', '').strip()
            if email and email not in emails:
                emails.append(email)
        
        # Also extract emails from job description text (handles edge cases)
        if job_description:
            from utils import extract_emails
            text_emails = extract_emails(job_description)
            for email in text_emails:
                if email not in emails:
                    emails.append(email)
        
        # Extract company name from the description (usually in bold at the start)
        company_name = "Unknown Company"
        if job_description:
            # Try to extract company name from the beginning of the description
            lines = job_description.split('\n')
            if lines:
                first_line = lines[0].strip()
                # Company name is often the first word or phrase before "is hiring"
                if 'is hiring' in first_line:
                    company_name = first_line.split('is hiring')[0].strip()
                elif first_line:
                    company_name = first_line
        
        # Extract job title from description
        job_title = "Unknown Job"
        if job_description:
            # Look for job title patterns
            for line in job_description.split('\n'):
                line = line.strip()
                if 'Engineer' in line or 'Developer' in line or 'Manager' in line:
                    job_title = line
                    break
            # Fallback to generic title if not found
            if job_title == "Unknown Job":
                if 'Engineer' in job_description:
                    job_title = "Engineer"
                elif 'Developer' in job_description:
                    job_title = "Developer"
                elif 'Manager' in job_description:
                    job_title = "Manager"
        
        # Extract location from description
        location = "Unknown Location"
        if job_description:
            if 'Remote' in job_description:
                location = "Remote"
            elif 'Bangalore' in job_description:
                location = "Bangalore"
            elif 'India' in job_description:
                location = "India"
        
        # Extract post URL (typically the job link)
        post_url = ""
        job_link = job_post.find('a', href=lambda x: x and 'linkedin.com/jobs/view' in str(x))
        if job_link:
            post_url = job_link.get('href', '').strip()
        else:
            # Fallback to any link with urn:li
            fallback_link = job_post.find('a', href=lambda x: x and 'urn:li:' in str(x))
            if fallback_link:
                post_url = fallback_link.get('href', '').strip()
        
        # Extract author (poster name) from the specific HTML structure
        author = "Unknown"
        # Look for author name in span inside p tag with specific class pattern
        author_p = job_post.find('p', class_=lambda x: x and '_893f12ae' in str(x))
        if author_p:
            author_span = author_p.find('span')
            if author_span:
                author = author_span.get_text().strip()
        
        # Fallback: try to extract from any span with text that looks like a name
        if author == "Unknown":
            for span in job_post.find_all('span'):
                text = span.get_text().strip()
                # Check if it looks like a name (2+ words, no special characters, reasonable length)
                if len(text.split()) >= 2 and len(text) < 50 and text[0].isupper():
                    # Avoid common non-name patterns
                    if not any(word in text.lower() for word in ['hiring', 'looking', 'we are', 'role', 'position', 'experience', 'location']):
                        author = text
                        break
        
        # Fallback: try to extract from /in/ links
        if author == "Unknown":
            author_link = job_post.find('a', href=lambda x: x and '/in/' in str(x))
            if author_link:
                author_elem = author_link.find('span')
                if author_elem:
                    author = author_elem.get_text().strip()
        
        # Extract author URL
        author_url = ""
        author_link = job_post.find('a', href=lambda x: x and '/in/' in str(x))
        if author_link:
            author_url = author_link.get('href', '')
        
        return {
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
        }
    except Exception as e:
        logger.warning(f"Error extracting job data: {e}")
        return None

def parse_post_card(link_elem, existing_urls: set) -> dict:
    """
    Parses a single LinkedIn post/update card starting from its unique update link element.
    Returns a dict with author, post_url, text, emails, post_date, and query_keyword, or None.
    """
    post_url = link_elem.get('href', '').strip()
    if not post_url:
        return None
        
    # Standardize relative URLs if any
    if not post_url.startswith('http'):
        post_url = f"https://www.linkedin.com{post_url}"
        
    # If we already have this post in pipeline.md, skip early
    if post_url in existing_urls:
        return {"status": "duplicate", "url": post_url}
        
    # Climb up 4 levels to find the entire post card container
    container = link_elem.parent.parent.parent.parent
    if not container:
        return None
        
    # 2. Extract Author Name and Profile Link (Supporting /in/ and /company/)
    author_name = "Unknown Poster"
    author_url = ""
    profile_links = container.find_all('a', href=lambda x: x and ('/in/' in x or '/company/' in x))
    for p_link in profile_links:
        p_text = p_link.get_text().strip()
        if p_text:
            clean_name = p_text.split('•')[0].strip()
            # No filtering - capture whatever name is found
            if clean_name:
                author_name = clean_name
                author_url = p_link['href']
                if not author_url.startswith('http'):
                    author_url = f"https://www.linkedin.com{author_url}"
                break
                
    if not author_url and profile_links:
        author_url = profile_links[0]['href']
        if not author_url.startswith('http'):
            author_url = f"https://www.linkedin.com{author_url}"
            
    # 3. Extract Post Commentary Content (No filtering)
    p_tags = container.find_all(['p', 'span'])
    body_candidates = []
    
    for p in p_tags:
        text = p.get_text().strip()
        # No length filtering - capture all text
        if text:
            # No keyword filtering - capture all text
            if text not in body_candidates:
                body_candidates.append(text)
            
    body_text = ""
    if body_candidates:
        # Sort candidates by length; the longest block of text is virtually always the post description
        body_candidates.sort(key=len, reverse=True)
        body_text = body_candidates[0]
        
    # If no body text found, use placeholder instead of returning None
    if not body_text:
        body_text = "[No text content available]"
        
    # 4. Parse Emails
    emails = extract_emails(body_text)
    
    # 5. Post Date / Relative Time
    post_date = "Recent"
    # Find relative dates (typically like '1d', '3h', '5d', '2 weeks ago', etc.) in subtext tags
    subtexts = container.find_all(class_=lambda x: x and ('sub-text' in x or 'actor__subtext' in x or 'time-distributor' in x))
    for st in subtexts:
        st_text = st.get_text().strip()
        if st_text:
            parts = st_text.split('•')
            candidate_date = parts[0].strip()
            if re.match(r'^\d+[dmwyh]', candidate_date) or "ago" in candidate_date:
                post_date = candidate_date
                break
                
    return {
        "status": "new",
        "author": author_name,
        "author_url": author_url,
        "post_url": post_url,
        "text": body_text,
        "emails": emails,
        "date": post_date
    }

def append_to_pipeline(post_data: dict, keyword: str):
    """Appends a successfully scraped post to pipeline.md."""
    logger.info(f"Writing post to pipeline.md - Author: '{post_data['author']}' | Emails: {post_data['emails']} | URL: {post_data['post_url']}")
    file_exists = os.path.exists(PIPELINE_FILE)
    
    with open(PIPELINE_FILE, 'a', encoding='utf-8') as f:
        if not file_exists:
            # Write pipeline header
            f.write("# LinkedIn Lead Automation Pipeline\n\n")
            f.write("This file is automatically updated by the LinkedIn post scraper. It is designed to feed into an automated email system. Change status from `Pending` to `Emailed` or `Skipped` once processed.\n\n")
            f.write("---\n\n")
            
        # Write post data in a structured markdown block
        f.write(f"### Post by {post_data['author']}\n")
        if post_data['author_url']:
            f.write(f"- **Author Profile**: {post_data['author_url']}\n")
        f.write(f"- **Post URL**: {post_data['post_url']}\n")
        
        # Email parsing results
        emails = post_data['emails']
        if emails:
            emails_str = ", ".join([f"`{e}`" for e in emails])
            status_str = "Pending"
        else:
            emails_str = "`None`"
            status_str = "Skipped"  # Skipped so the email sender ignores it
            
        f.write(f"- **Parsed Emails**: {emails_str}\n")
        f.write(f"- **Search Keyword**: `{keyword}`\n")
        f.write(f"- **Scraped Date/Relative Time**: `{post_data['date']}`\n")
        f.write(f"- **Scraping Timestamp**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n")
        f.write(f"- **Status**: `{status_str}` <!-- AUTOMATION_STATUS -->\n")
        f.write("- **Email Sent**: `No` <!-- AUTOMATION_SENT -->\n")
        f.write("\n**Full Post Content:**\n")
        
        # Indent content block inside a quote block for neatness
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

def run_scraper():
    """Main scraping orchestrator."""
    logger.info("Initializing LinkedIn Content Scraper...")
    console.print(Panel.fit(
        "[bold green]LinkedIn Automated Post Lead Scraper[/bold green]\n"
        "[white]Connecting to active Chrome browser & scraping content feeds...[/white]"
    ))
    
    # Load keywords from .env file
    keywords = load_keywords_from_env()
    
    # Ensure pipeline file exists so it is visible in the workspace
    initialize_pipeline_file()
    
    # Load already scraped URLs to avoid duplicating entries
    existing_urls = load_existing_urls(PIPELINE_FILE)
    
    with sync_playwright() as p:
        try:
            msg_conn = f"Connecting to Google Chrome at {CHROME_CDP_URL}..."
            logger.info(msg_conn)
            console.print(f"[blue]{msg_conn}[/blue]")
            # Connect to running Chrome instance via CDP
            browser = p.chromium.connect_over_cdp(CHROME_CDP_URL)
            logger.info("Successfully connected to Chrome via CDP.")
            
            # Check if we have contexts, use existing or create new
            if len(browser.contexts) > 0:
                context = browser.contexts[0]
            else:
                context = browser.new_context()
                
            page = context.new_page()
            
            # Set a high-quality user-agent just in case
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            # To track stats
            total_scraped_posts = 0
            total_new_leads_with_emails = 0
            
            for keyword in keywords:
                console.print(Panel(f"[bold cyan]Scraping Keyword: '{keyword}'[/bold cyan]"))
                
                # Encode search parameters
                encoded_keyword = urllib.parse.quote(keyword)
                search_url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_keyword}&origin=CLUSTER_EXPANSION"
                
                msg_search = f"Navigating to search URL: {search_url}"
                logger.info(msg_search)
                console.print(f"[blue]{msg_search}[/blue]")
                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as goto_err:
                    logger.warning(f"page.goto timeout/warning: {goto_err}")
                
                # Wait for container or check if login required
                try:
                    # Give it a bit of time to render or redirect
                    page.wait_for_timeout(4000)
                    
                    if "login" in page.url or "checkpoint" in page.url:
                        err_msg = f"CRITICAL: LinkedIn redirected to Login or Security Checkpoint: {page.url}"
                        logger.error(err_msg)
                        console.print(f"[bold red]{err_msg}[/bold red]")
                        console.print("[bold red]Please log into LinkedIn in your opened Chrome instance first, then rerun this script![/bold red]")
                        return
                        
                    # Wait for search results container or feed update cards
                    page.wait_for_selector('[data-testid="lazy-column"], .reusable-search__result-container, .feed-shared-update-v2, .search-results-container', timeout=15000)
                    logger.info("Search results selector resolved successfully.")
                except Exception as e:
                    logger.warning(f"Timeout or error waiting for search results container: {e}. Attempting scroll anyway...")
                    console.print("[yellow]Timeout waiting for search results selector. Let's try scrolling anyway...[/yellow]")
                
                # Scroll to load dynamic contents and click expanders
                logger.info(f"Scrolling {SCROLL_STEPS} times to load posts for keyword: '{keyword}'")
                console.print(f"[blue]Scrolling {SCROLL_STEPS} times to lazy-load posts and expanding truncated texts...[/blue]")
                
                keyword_scraped_count = 0
                keyword_lead_count = 0
                
                for step in range(SCROLL_STEPS):
                    # Step 1: Expand all "see more" buttons currently visible
                    try:
                        # Match '...more', '… more', 'see more', 'See more', etc., on any button, span, or anchor
                        see_more_locator = page.locator("button, span, a").filter(has_text=re.compile(r'(?:\.\.\.|…)\s*more|see\s+more', re.I))
                        count = see_more_locator.count()
                        clicked = 0
                        for idx in range(count):
                            btn = see_more_locator.nth(idx)
                            if btn.is_visible():
                                try:
                                    btn.click(timeout=1000)
                                    clicked += 1
                                except Exception:
                                    pass
                        if clicked > 0:
                            console.print(f"  [grey62]Expanded {clicked} truncated posts on scroll step {step+1}[/grey62]")
                    except Exception as see_more_err:
                        logger.warning(f"Error locating/expanding see more buttons: {see_more_err}")
                    
                    # Step 2: Log all posts currently visible (after expansion)
                    try:
                        html_content = page.content()
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Find job posts using componentkey attribute
                        job_posts = soup.find_all('div', attrs={'componentkey': lambda x: x and 'FeedType_FLAGSHIP_SEARCH' in str(x)})
                        
                        logger.info(f"Scroll step {step+1}: Found {len(job_posts)} job posts on page.")
                        
                        # Process each job post
                        for job_post in job_posts:
                            try:
                                # Extract job data from the job post HTML
                                job_data = extract_job_data(job_post)
                                if not job_data:
                                    continue
                                    
                                # Check for duplicates
                                if job_data.get("post_url") in existing_urls:
                                    continue
                                    
                                # Standardize data extraction
                                post_url = job_data["post_url"]
                                emails = job_data["emails"]
                                
                                keyword_scraped_count += 1
                                total_scraped_posts += 1
                                
                                # Append the post into pipeline.md (acts as full audit trail / log first)
                                append_to_pipeline(job_data, keyword)
                                existing_urls.add(post_url)  # Prevent duplicates in other sections
                                
                                if emails:
                                    keyword_lead_count += 1
                                    total_new_leads_with_emails += 1
                                    console.print(f"  [bold green]✓ Lead Found (With Email)[/bold green] - Author: [bold]{job_data['author']}[/bold] | Emails: {emails}")
                                else:
                                    console.print(f"  [grey62]○ Logged Post (No Email)[/grey62] - Author: [bold]{job_data['author']}[/bold]")
                                
                            except Exception as e:
                                # Log error silently and continue
                                continue
                                
                    except Exception as parse_err:
                        logger.warning(f"Error parsing posts on scroll step {step+1}: {parse_err}")
                    
                    # Step 3: Scroll to load more content
                    try:
                        page.evaluate("""() => {
                            window.scrollTo(0, document.body.scrollHeight);
                            const el = document.getElementById('workspace') || document.querySelector('main');
                            if (el) {
                                el.scrollTo(0, el.scrollHeight);
                            }
                        }""")
                    except Exception as scroll_err:
                        logger.warning(f"Scroll step {step+1} evaluate error (context might be reloading): {scroll_err}")
                        page.wait_for_timeout(2000)
                        continue
                        
                    page.wait_for_timeout(SCROLL_DELAY_MS)
                
                msg_summary = f"Keyword '{keyword}' summary: Analyzed {keyword_scraped_count} new posts, found {keyword_lead_count} new email leads."
                logger.info(msg_summary)
                console.print(f"[cyan]{msg_summary}[/cyan]\n")
            
            # Print beautiful final report
            msg_final = f"LinkedIn Scraper run completed. Total keywords: {len(keywords)}, Analyzed: {total_scraped_posts}, New email leads: {total_new_leads_with_emails}"
            logger.info(msg_final)
            
            report_table = Table(title="LinkedIn Scraper Completion Report")
            report_table.add_column("Metric", style="bold magenta")
            report_table.add_column("Count", style="bold green")
            report_table.add_row("Total Keywords Searched", str(len(keywords)))
            report_table.add_row("Total New Posts Analyzed", str(total_scraped_posts))
            report_table.add_row("Total New Email Leads Saved", str(total_new_leads_with_emails))
            report_table.add_row("Output File", PIPELINE_FILE)
            
            console.print(Panel(report_table))
            console.print("[bold green]✔ Scraper run completed successfully! Leads saved in pipeline.md.[/bold green]")
            
        except Exception as e:
            logger.exception(f"Critical error during scraper run: {e}")
            console.print(f"[bold red]CRITICAL SCRAPER ERROR: {e}[/bold red]")
            console.print("[yellow]Please ensure Chrome is running on port 9222. Execute command:[/yellow]")
            console.print("[bold white]/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222[/bold white]")

if __name__ == "__main__":
    run_scraper()
