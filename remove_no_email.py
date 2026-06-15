#!/usr/bin/env python3
"""
Remove job postings without email addresses from pipeline.md.
"""

import re

def remove_no_email(input_file, output_file):
    """Remove posts without email addresses."""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content into individual posts
    posts = re.split(r'\n---\n', content)
    
    posts_with_email = []
    
    for post in posts:
        if not post.strip():
            continue
        
        # Extract parsed emails
        email_match = re.search(r'- \*\*Parsed Emails\*\*: (.*?)\n', post)
        if email_match:
            emails = email_match.group(1).strip()
            # Keep post if it has emails (not None and not empty)
            if emails and emails != 'None' and emails != '':
                posts_with_email.append(post)
        else:
            # Keep posts without email field (edge case)
            posts_with_email.append(post)
    
    # Rebuild content
    filtered_content = '\n---\n'.join(posts_with_email)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(filtered_content)
    
    print(f"Removed {len(posts) - len(posts_with_email)} posts without email")
    print(f"Kept {len(posts_with_email)} posts with email")

if __name__ == "__main__":
    remove_no_email('pipeline.md', 'pipeline.md')
