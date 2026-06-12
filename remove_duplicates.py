#!/usr/bin/env python3
"""
Remove duplicate job postings from pipeline.md based on post URL.
Keeps the first occurrence of each unique post URL (excluding tracking IDs).
"""

import re
from urllib.parse import urlparse, parse_qs

def extract_base_url(url):
    """Extract base URL without tracking ID parameter."""
    if not url or url.strip() == '':
        return None
    
    # Remove trackingId parameter from URL
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Remove trackingId if present
    if 'trackingId' in query_params:
        del query_params['trackingId']
    
    # Rebuild URL without trackingId
    if query_params:
        new_query = '&'.join([f"{k}={v[0]}" for k, v in query_params.items()])
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
    else:
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    return base_url

def remove_duplicates(input_file, output_file):
    """Remove duplicate posts based on base URL."""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content into individual posts
    posts = re.split(r'\n---\n', content)
    
    seen_urls = set()
    unique_posts = []
    
    for post in posts:
        if not post.strip():
            continue
        
        # Extract post URL
        url_match = re.search(r'- \*\*Post URL\*\*: (.*?)\n', post)
        if url_match:
            url = url_match.group(1).strip()
            base_url = extract_base_url(url)
            
            if base_url and base_url not in seen_urls:
                seen_urls.add(base_url)
                unique_posts.append(post)
            elif not base_url:
                # Keep posts with empty URLs
                unique_posts.append(post)
        else:
            # Keep posts without URL field
            unique_posts.append(post)
    
    # Rebuild content
    deduplicated_content = '\n---\n'.join(unique_posts)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(deduplicated_content)
    
    print(f"Removed {len(posts) - len(unique_posts)} duplicate posts")
    print(f"Kept {len(unique_posts)} unique posts")

if __name__ == "__main__":
    remove_duplicates('pipeline.md', 'pipeline.md')
