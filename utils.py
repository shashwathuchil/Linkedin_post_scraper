import re
import html
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Set

def setup_logger(log_file: str = "scraper.log") -> logging.Logger:
    """Configures a rotating file logger for persistent application logging."""
    logger = logging.getLogger("linkedin_scraper")
    logger.setLevel(logging.INFO)
    
    # Avoid adding duplicate handlers if setup is called multiple times
    if not logger.handlers:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
    return logger

def clean_text(text: str) -> str:
    """Cleans up HTML entities and standardizes whitespaces."""
    if not text:
        return ""
    # Decode HTML entities (e.g. &amp;, &lt;, &#39;)
    text = html.unescape(text)
    # Replace multiple spaces/newlines with clean spacing
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_emails(text: str) -> List[str]:
    """
    Extracts and standardizes emails from a given text.
    Handles standard formats and various obfuscation patterns:
    - user@domain.com
    - user [at] domain [dot] com
    - user(at)domain(dot)com
    - user at domain dot com
    - user AT domain.com
    - user @ domain . com
    """
    if not text:
        return []
    
    found_emails: Set[str] = set()
    
    # 1. Clean the text slightly for standard processing
    normalized = text.lower()
    
    # 2. Pattern to find standard emails with word boundaries
    # [a-zA-Z0-9._%+-]+ @ [a-zA-Z0-9.-]+ \. [a-zA-Z]{2,}
    standard_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    for match in re.findall(standard_pattern, normalized):
        # Clean any trailing periods or noise
        email = match.strip().strip('.')
        # Quick validation of format
        if re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            # Additional validation: ensure domain has at least one dot and valid TLD
            if '.' in email.split('@')[1] and len(email.split('@')[1].split('.')[-1]) >= 2:
                # Check for concatenated name patterns (e.g., user@domain.comname)
                domain = email.split('@')[1]
                # If the last part of domain is very long (>15 chars), might be concatenated name
                if len(domain.split('.')[-1]) > 15:
                    continue
                # If the domain has more than 4 parts, might be concatenated
                if len(domain.split('.')) > 4:
                    continue
                found_emails.add(email)
            
    # 3. Pattern to find common obfuscated emails:
    # Captures: username [at] domain [dot] com, username(at)domain.com, etc.
    # We define AT and DOT patterns with strict word boundaries and brackets
    at_pattern = r'\s*(?:[\(\[\{<]\s*(?:at|@)\s*[\)\]\}>]|\bat\b|@)\s*'
    dot_pattern = r'\s*(?:[\(\[\{<]\s*(?:dot|\.)\s*[\)\]\}>]|\bdot\b|\.)\s*'
    
    # This matches: <username> <at_pattern> <domain_part1> <dot_pattern> <domain_part2>
    obfuscated_pattern = rf'([a-zA-Z0-9._%+-]+){at_pattern}([a-zA-Z0-9.-]+){dot_pattern}([a-zA-Z]{{2,}})'
    
    for match in re.finditer(obfuscated_pattern, normalized):
        username, domain_part1, domain_part2 = match.groups()
        
        # Avoid false positives like "hiring at 10am" or "looking at some.pdf"
        # We check that the username doesn't contain common English stop words
        # and that the domain looks reasonable
        if username in {
            'hiring', 'looking', 'working', 'posted', 'updated', 'sharing', 'meet', 'join', 'start',
            'us', 'me', 'we', 'you', 'it', 'him', 'her', 'them', 'here', 'there', 'who', 'how', 'why', 'what'
        }:
            continue
            
        # Reconstruct standard email
        email = f"{username}@{domain_part1}.{domain_part2}"
        # Remove any leftover spaces or brackets
        email = re.sub(r'[\s\(\)\[\]\{\}<>]', '', email)
        
        # Filter out false positives matching www. prefix (websites)
        if "www." in email:
            continue
        
        # Validate format
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            found_emails.add(email)
            
    # Let's also search for emails with subdomains obfuscated (e.g. shashwath [at] gmail [dot] co [dot] in)
    # We do a replacement of AT and DOT if they are in bracketed format to be safe
    safe_normalized = normalized
    # Replace bracketed ATs
    safe_normalized = re.sub(r'\s*[\[\(\{<]at[\]\)\}>]\s*', '@', safe_normalized)
    # Replace bracketed DOTs
    safe_normalized = re.sub(r'\s*[\[\(\{<]dot[\]\)\}>]\s*', '.', safe_normalized)
    
    # Run the standard email regex on this safely-un-obfuscated text
    for match in re.findall(standard_pattern, safe_normalized):
        email = match.strip().strip('.')
        # Additional validation: ensure email doesn't contain common name patterns
        # Check if the email is concatenated with a name (e.g., user@domain.comname)
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            # Check for suspicious patterns like email followed by lowercase name
            local_part = email.split('@')[0]
            domain = email.split('@')[1]
            # If the domain part looks like it has a name appended, skip it
            if len(domain.split('.')) > 3:  # Too many subdomains might indicate concatenation
                continue
            # If the local part is very long, might be concatenated
            if len(local_part) > 30:
                continue
            # Check for incomplete emails (missing proper TLD)
            tld = domain.split('.')[-1]
            # Valid TLDs should be at least 2 chars and not look like a name
            if len(tld) < 2 or len(tld) > 10:
                continue
            # Common invalid TLD patterns (names, common words)
            invalid_tlds = ['name', 'email', 'mail', 'contact', 'hr', 'cv', 'resume', 'shukla', 'gupta', 'kumar', 'singh', 'sharma', 'verma', 'agarwal', 'jain', 'patel', 'rao', 'nair', 'iyer', 'goyal', 'mehta', 'kapoor', 'malhotra', 'chopra', 'dixit', 'saxena', 'sharma', 'tiwari', 'pandey', 'mishra', 'yadav', 'singh', 'das', 'sahu', 'paul', 'sen', 'bose', 'chatterjee', 'mukherjee', 'banerjee', 'chakraborty', 'ghosh', 'dutta', 'roy', 'das', 'pal', 'mondal', 'sarkar', 'biswas', 'choudhury', 'khan', 'ali', 'ahmed', 'hussain', 'shaikh', 'siddiqui', 'farooqui', 'qureshi', 'malik', 'ansari', 'hussain', 'rashid', 'akhtar', 'zafar', 'hameed', 'rehman', 'siddique', 'haque', 'khan', 'malik', 'hussain', 'ali', 'ahmed', 'rehman', 'siddiqui', 'farooq', 'qureshi', 'shah', 'syed', 'hussain', 'rashid', 'akhtar', 'zafar', 'hameed', 'rehman', 'siddique', 'haque']
            if tld.lower() in invalid_tlds:
                continue
            # Check if TLD contains only letters (valid TLDs are alphabetic)
            if not tld.isalpha():
                continue
            found_emails.add(email)
            
    # Clean up and return as sorted list
    return sorted(list(found_emails))

# Simple test suite to run inline or verify
if __name__ == "__main__":
    test_cases = [
        "Please send CV to shashwath@gmail.com",
        "Reach out at shashwath [at] gmail [dot] com for referrals",
        "My email is shashwath(at)gmail.co.in thanks!",
        "Hiring at 10am in San Francisco (not an email)",
        "contact shashwath at gmail dot com",
        "Send resume to shashwath@gmail.co.uk",
        "email: shashwath.work@domain-name.co"
    ]
    
    print("Running Email Parser Tests:")
    for text in test_cases:
        emails = extract_emails(text)
        print(f"Text: '{text}'")
        print(f"Extracted: {emails}\n")
