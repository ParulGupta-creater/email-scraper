from collections import deque
import urllib.parse
import re
from bs4 import BeautifulSoup
import requests
import requests.exceptions as request_exception

# === Utility Functions ===
def get_base_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f'{parts.scheme}://{parts.netloc}'

def get_page_path(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return url[:url.rfind('/') + 1] if '/' in parts.path else url

def normalize_link(link: str, base_url: str, page_path: str) -> str:
    if not link: return ""
    link = link.strip()
    if link.startswith('//'): return 'https:' + link
    if link.startswith('/'): return base_url + link
    if not link.startswith('http'): return page_path + link
    return link

def clean_text(text: str) -> str:
    text = text.lower()
    obfuscations = {
        r'\[at\]': '@', r'\(at\)': '@', r'\s+at\s+': '@',
        r'\[dot\]': '.', r'\(dot\)': '.', r'\s+dot\s+': '.',
        r'\[@\]': '@', r'\[\.\]': '.',
        r'\s*\[?\s*at\s*\]?\s*': '@',
        r'\s*\[?\s*dot\s*\]?\s*': '.',
    }
    for pattern, replacement in obfuscations.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def extract_emails(text: str) -> set[str]:
    cleaned = clean_text(text)
    email_pattern = r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}'
    return set(re.findall(email_pattern, cleaned, re.I))

def extract_emails_from_footer(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    return extract_emails(str(footer)) if footer else set()

def is_valid_email(email: str) -> bool:
    blocked_domains = [
        'googlesyndication.com', 'ads.', 'sentry.', 'wixpress.com',
        'bodis.com', 'akamai.net', 'cloudflare.net', 'amazonaws.com'
    ]
    if (
        re.search(r'\.(webp|png|jpg|jpeg|html|css|svg|js)$', email) or
        any(bad in email for bad in blocked_domains) or
        email.startswith('.') or
        len(email.split('@')[1].split('.')[0]) < 3
    ):
        return False
    return True

def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    priority_keywords = ['guest', 'write', 'editor', 'submit', 'contact', 'info', 'tips', 'outreach']
    priority = [e for e in emails if any(k in e for k in priority_keywords)]
    others = [e for e in emails if e not in priority]
    return priority, others

# === Scraper Core ===
def scrape_website(start_url: str, max_count: int = 3) -> set[str] | str:
    base_url = get_base_url(start_url)
    urls_to_process = deque()
    scraped_urls = set()
    collected_emails = set()
    contact_form_found = False
    count = 0

    # Priority pages
    priority_paths = [
        '/contact', '/contact-us', '/write-for-us', '/guest-post',
        '/contribute', '/submit-guest-post', '/become-a-contributor',
        '/submit-post', '/editorial-guidelines'
    ]
    for path in priority_paths:
        urls_to_process.append(base_url + path)
    urls_to_process.append(start_url)  # Fallback: homepage last

    while urls_to_process and count < max_count:
        url = urls_to_process.popleft()
        if url in scraped_urls:
            continue
        scraped_urls.add(url)
        count += 1

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except (request_exception.RequestException, request_exception.MissingSchema, request_exception.ConnectionError):
            continue

        html = response.text
        all_emails = extract_emails(html) | extract_emails_from_footer(html)
        valid_emails = {email for email in all_emails if is_valid_email(email)}
        collected_emails.update(valid_emails)

        if not collected_emails:
            text = html.lower()
            if '<form' in text and any(keyword in text for keyword in ['contact', 'write for us', 'submit a guest post']):
                contact_form_found = True

        soup = BeautifulSoup(html, 'lxml')
        page_path = get_page_path(url)
        for a in soup.find_all('a'):
            link = a.get('href', '')
            normalized = normalize_link(link, base_url, page_path)
            if any(p in normalized.lower() for p in ['write', 'guest', 'contact', 'submit']):
                if normalized not in urls_to_process and normalized not in scraped_urls:
                    urls_to_process.append(normalized)

    if collected_emails:
        priority, others = prioritize_emails(collected_emails)
        return set(priority) if priority else set(others)
    elif contact_form_found:
        return "Contact Form"
    else:
        return "No Email"
