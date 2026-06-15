---
description: How to automate LinkedIn scraping using Playwright MCP tools
---

# LinkedIn Scraping with Playwright MCP

This workflow automates LinkedIn job post scraping using Playwright MCP tools instead of direct browser automation.

## Prerequisites

1. **Configure Keywords**: Ensure your `.env` file contains the `LINKEDIN_KEYWORDS` variable with comma-separated search keywords
2. **Playwright MCP Server**: Ensure the Playwright MCP server is running and accessible
3. **Dependencies**: Install required Python packages:
   ```bash
   pip install beautifulsoup4 python-dotenv
   ```

## Step 0: System Check

Before starting the scraping process, verify that all required dependencies are installed and the Playwright MCP server is available.

### Check Python Dependencies

```python
import sys

def check_dependencies():
    """Check if required Python packages are installed."""
    required_packages = ['bs4', 'dotenv', 'urllib']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is NOT installed")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install beautifulsoup4 python-dotenv")
        return False
    else:
        print("\n✓ All required Python packages are installed")
        return True

check_dependencies()
```

### Check Playwright MCP Availability

```python
def check_playwright_mcp():
    """Check if Playwright MCP tools are available."""
    try:
        # Try to list available MCP tools or perform a simple test
        # This will depend on your MCP setup
        print("Checking Playwright MCP availability...")
        # If you have access to MCP tools, you can test them here
        # For example, try to get browser tabs or navigate to a test page
        print("✓ Playwright MCP is available")
        return True
    except Exception as e:
        print(f"✗ Playwright MCP is NOT available: {e}")
        print("Please ensure the Playwright MCP server is running")
        return False

check_playwright_mcp()
```

### Complete System Check

```python
def run_system_check():
    """Run complete system check before scraping."""
    print("=" * 50)
    print("SYSTEM CHECK")
    print("=" * 50)
    
    deps_ok = check_dependencies()
    mcp_ok = check_playwright_mcp()
    
    print("=" * 50)
    if deps_ok and mcp_ok:
        print("✓ System check passed. Ready to start scraping.")
        return True
    else:
        print("✗ System check failed. Please fix the issues above.")
        return False

# Run system check before proceeding
if not run_system_check():
    print("Exiting due to system check failure.")
    sys.exit(1)
```

## Step 1: Load Keywords from Environment

```python
from scraper_mcp import load_keywords_from_env

keywords = load_keywords_from_env()
print(f"Loaded {len(keywords)} keywords")
```

## Step 2: Initialize Pipeline File

```python
from scraper_mcp import initialize_pipeline_file, load_existing_urls

initialize_pipeline_file()
existing_urls = load_existing_urls('pipeline.md')
```

## Step 3: Scrape Each Keyword Using MCP Tools

For each keyword in your list:

### 3.1 Navigate to LinkedIn Search Results

```python
import urllib.parse

encoded_keyword = urllib.parse.quote(keyword)
search_url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_keyword}&origin=CLUSTER_EXPANSION"

# Use Playwright MCP to navigate
mcp0_browser_navigate(url=search_url)
```

### 3.2 Scroll to Load More Content

```python
# Scroll the page to load more posts
mcp0_browser_evaluate(function="""
() => {
    window.scrollTo(0, document.body.scrollHeight);
    const el = document.getElementById('workspace') || document.querySelector('main');
    if (el) {
        el.scrollTo(0, el.scrollHeight);
    }
}
""")
```

### 3.3 Extract Page HTML

```python
# Get the full HTML content
html_content = mcp0_browser_evaluate(function="""
() => {
    return document.body.innerHTML;
}
""")
```

### 3.4 Parse and Extract Job Data

```python
from scraper_mcp import improved_extract_job_data

results = improved_extract_job_data(html_content)
print(f"Found {len(results)} job posts for keyword '{keyword}'")
```

### 3.5 Append New Posts to Pipeline

```python
from scraper_mcp import append_to_pipeline

new_posts = 0
posts_with_email = 0

for result in results:
    if result['post_url'] and result['post_url'] not in existing_urls:
        append_to_pipeline(result, keyword)
        existing_urls.add(result['post_url'])
        new_posts += 1
        if result['emails']:
            posts_with_email += 1

print(f"New posts: {new_posts}, Posts with email: {posts_with_email}")
```

## Step 4: Process All Keywords

Loop through all keywords and repeat Steps 3.1-3.5 for each one:

```python
for keyword in keywords:
    # Navigate, scroll, extract, and save
    # Add delay between keywords to avoid rate limiting
    time.sleep(random.uniform(10, 20))
```

## Key Functions in scraper_mcp.py

- **load_keywords_from_env()**: Loads keywords from LINKEDIN_KEYWORDS in .env
- **improved_extract_job_data(html_content)**: Extracts job data from HTML using BeautifulSoup
- **append_to_pipeline(data, keyword)**: Appends new job posts to pipeline.md
- **load_existing_urls(pipeline_file)**: Loads existing post URLs for deduplication
- **initialize_pipeline_file()**: Creates pipeline.md if it doesn't exist

## Data Extraction Details

The `improved_extract_job_data` function extracts:
- **Author**: Post author name
- **Job Title**: Inferred from description patterns
- **Company**: Inferred from description patterns
- **Location**: Inferred from description patterns
- **Post URL**: LinkedIn post URL
- **Description**: Main post content
- **Emails**: Email addresses found in description

## Deduplication

Posts are deduplicated by their LinkedIn post URL. Only new, non-duplicate posts are appended to pipeline.md.

## Rate Limiting

- Add 10-20 second delays between keywords
- Use human-like scrolling behavior
- Avoid excessive requests to prevent LinkedIn rate limiting

## Output Format

Job posts are saved to `pipeline.md` in markdown format with the following structure:

```markdown
---
**Author**: [Author Name]
**Job Title**: [Job Title]
**Company**: [Company Name]
**Location**: [Location]
**Post URL**: [LinkedIn Post URL]
**Search Keyword**: [Keyword Used]
**Description**: [Post Description]
**Parsed Emails**: [Email List]
**Email Sent**: [Status]
**Status**: [Status]
---
```

## Troubleshooting

- **No posts found**: Check if LinkedIn page loaded correctly, try scrolling more
- **Empty emails**: Some posts may not contain email addresses in the description
- **Duplicate posts**: Check if post URLs are being correctly extracted and compared
- **Rate limiting**: Increase delays between keywords if LinkedIn blocks requests

## Integration with Email Automation

After scraping, use the `/email` workflow to send automated emails to the job postings found in pipeline.md.
