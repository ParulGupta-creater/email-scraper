from collections import deque
import urllib.parse
import re
from bs4 import BeautifulSoup
import requests
import requests.exceptions as request_exception

# 🌐 URL utilities
def get_base_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f'{parts.scheme}://{parts.netloc}'

def get_page_path(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return url[:url.rfind('/') + 1] if '/' in parts.path else url

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

# 🧹 Clean and extract emails
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

def extract_emails(text: str) -> set[str]:
    cleaned = clean_text(text)
    email_pattern = r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}'
    return set(re.findall(email_pattern, cleaned, re.I))

def extract_emails_from_html(html: str) -> set[str]:
    return extract_emails(html)

def extract_emails_from_footer(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    if footer:
        return extract_emails(str(footer))
    return set()

# 📬 Prioritize emails
def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    outreach_keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'outreach', 'media', 'contribute']
    priority = []
    others = []
    for email in emails:
        if any(kw in email for kw in outreach_keywords):
            priority.append(email)
        else:
            others.append(email)
    return priority, others

# 🕸️ Main scraping logic
def scrape_website(start_url: str, max_count: int = 3) -> set[str] | str:
    base_url = get_base_url(start_url)
    urls_to_process = deque()
    scraped_urls = set()
    collected_emails = set()
    count = 0
    contact_form_found = False

    priority_paths = [
        '/contact', '/contact-us', '/write-for-us', '/guest-post',
        '/contribute', '/submit-guest-post', '/become-a-contributor',
        '/submit-post', '/editorial-guidelines'
    ]

    for path in priority_paths:
        urls_to_process.append(base_url + path)

    urls_to_process.append(start_url)

    while urls_to_process and count < max_count:
        url = urls_to_process.popleft()
        if url in scraped_urls:
            continue

        scraped_urls.add(url)
        page_path = get_page_path(url)
        count += 1

        print(f'[{count}] Processing {url}')

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except (request_exception.RequestException, request_exception.MissingSchema, request_exception.ConnectionError):
            continue

        page_html = response.text

        # Extract all and footer-specific emails
        all_emails = extract_emails_from_html(page_html) | extract_emails_from_footer(page_html)

        # Filtering logic
        filtered_emails = {
            email for email in all_emails
            if (
                '@' in email and
                not email.lower().startswith(('http', 'https', 'www')) and
                '%' not in email and
                not any(bad in email.lower() for bad in [
                    'googlesyndication', 'doubleclick', 'aset.', 'wh@sapp.com', 'beehiiv.com',
                    'widget', 'template', 'ads.', 'author@', 'noreply', 'ion.', 'ung.', 'boden.'
                ]) and
                re.match(r'^[a-z0-9._%+-]{3,}@[a-z0-9.-]+\.(com|org|net|edu|co|io)$', email, re.I)
            )
        }

        collected_emails.update(filtered_emails)

        # Check for contact form
        text = page_html.lower()
        if '<form' in text and any(kw in text for kw in ['contact', 'write for us', 'submit a guest post', 'contribute']):
            contact_form_found = True

        # Follow more guest/contact links
        soup = BeautifulSoup(page_html, 'lxml')
        for anchor in soup.find_all('a'):
            link = anchor.get('href', '')
            normalized = normalize_link(link, base_url, page_path)
            if any(p in normalized.lower() for p in ['write', 'guest', 'contact', 'submit']):
                if normalized not in urls_to_process and normalized not in scraped_urls:
                    urls_to_process.append(normalized)

    # Final prioritization and result
    if collected_emails:
        priority, others = prioritize_emails(collected_emails)
        return set(priority) if priority else set(others)
    elif contact_form_found:
        return "Contact Form"
    else:
        return "No Email"
