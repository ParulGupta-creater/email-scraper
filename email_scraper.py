from collections import deque
import urllib.parse
import re
from bs4 import BeautifulSoup
import requests
import requests.exceptions as request_exception

# Helper: Normalize base URL
def get_base_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f'{parts.scheme}://{parts.netloc}'

# Helper: Page path for relative links
def get_page_path(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return url[:url.rfind('/') + 1] if '/' in parts.path else url

# Helper: Normalize hrefs
def normalize_link(link: str, base_url: str, page_path: str) -> str:
    if not link:
        return ""
    link = link.strip()
    if link.startswith('//'):
        return 'https:' + link
    elif link.startswith('/'):
        return base_url + link
    elif not link.startswith('http'):
        return page_path + link
    return link

# Clean text for email obfuscations
def clean_text(text: str) -> str:
    text = text.lower()
    obfuscations = {
        r'\[at\]': '@', r'\(at\)': '@', r'\s+at\s+': '@',
        r'\[dot\]': '.', r'\(dot\)': '.', r'\s+dot\s+': '.',
        r'\[@\]': '@', r'\[\.\]': '.', r'\s*\[?\s*at\s*\]?\s*': '@',
        r'\s*\[?\s*dot\s*\]?\s*': '.',
    }
    for pattern, replacement in obfuscations.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# Extract emails from HTML content
def extract_emails(html: str) -> set[str]:
    cleaned = clean_text(html)
    pattern = r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}'
    return set(re.findall(pattern, cleaned, re.I))

# Extract emails specifically from the <footer>
def extract_footer_emails(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    if footer:
        return extract_emails(str(footer))
    return set()

# Email priority filtering
def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    outreach_keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority, others = [], []
    for email in emails:
        if any(kw in email for kw in outreach_keywords):
            priority.append(email)
        else:
            others.append(email)
    return priority, others

# ✅ Main scraping logic
def scrape_website(start_url: str, max_count: int = 3) -> set[str] | str:
    base_url = get_base_url(start_url)
    urls_to_process = deque()
    scraped_urls = set()
    collected_emails = set()
    count = 0
    contact_form_found = False

    # High priority guest post / contact pages
    priority_paths = [
        '/contact', '/contact-us', '/write-for-us', '/guest-post', '/contribute',
        '/submit-guest-post', '/become-a-contributor', '/submit-post', '/editorial-guidelines'
    ]
    for path in priority_paths:
        urls_to_process.append(base_url + path)
    urls_to_process.append(start_url)  # homepage last

    while urls_to_process and count < max_count:
        url = urls_to_process.popleft()
        if url in scraped_urls:
            continue
        scraped_urls.add(url)
        count += 1
        page_path = get_page_path(url)

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except (request_exception.RequestException, request_exception.MissingSchema, request_exception.ConnectionError):
            continue

        html = response.text

        # Extract and combine
        emails = extract_emails(html) | extract_footer_emails(html)

        # Filter out junk / auto-generated / 1-char domains / known spam sources
                filtered = {
            e for e in emails
            if not re.search(r'\.(png|jpg|jpeg|svg|css|js|webp|html)$', e)
            and not any(bad in e for bad in [
                'sentry', 'wixpress', 'cloudflare', 'gravatar', '@e.com', '@aset.', '@ar.com',
                'noreply@', 'amazonaws', 'akamai', 'doubleclick', 'pagead2.', 'googlemail',
                'wh@sapp.com', 'buyth@hotel.com'
            ])
            and not re.search(r'https?%3[a-z0-9]*@', e, re.I)  # avoid encoded URLs in emails
            and not re.search(r'www\.', e.split('@')[0], re.I)  # avoid email usernames like www.buyth@
            and not e.startswith('.') and '@' in e
            and re.search(r'@[\w.-]+\.(com|org|net|edu|co|io)$', e, re.I)
            and len(e.split('@')[1].split('.')[0]) >= 3  # valid domain before TLD
            and len(e.split('@')[0]) >= 3  # valid username
        }


        collected_emails.update(filtered)

        # If no emails, check for contact form signals
        if not collected_emails:
            lower_html = html.lower()
            if '<form' in lower_html and any(kw in lower_html for kw in ['contact', 'write for us', 'submit', 'reach us']):
                contact_form_found = True

        # Discover new links with priority keywords
        soup = BeautifulSoup(html, 'lxml')
        for anchor in soup.find_all('a'):
            link = anchor.get('href', '')
            normalized = normalize_link(link, base_url, page_path)
            if any(p in normalized.lower() for p in ['write', 'guest', 'contact', 'submit']):
                if normalized not in urls_to_process and normalized not in scraped_urls:
                    urls_to_process.append(normalized)

    # Return best match
    if collected_emails:
        priority, others = prioritize_emails(collected_emails)
        return set(priority) if priority else set(others)
    elif contact_form_found:
        return "Contact Form"
    else:
        return "No Email"
