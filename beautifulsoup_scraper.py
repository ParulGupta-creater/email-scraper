from collections import deque
import urllib.parse
import re
import requests
from bs4 import BeautifulSoup

# --- Logging ---
def log(msg):
    print(f"[DEBUG] {msg}")

# --- URL Normalization Helpers ---
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

# --- Email Extraction Helpers ---
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

def extract_emails(html: str) -> set[str]:
    cleaned = clean_text(html)
    pattern = r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}'
    raw_emails = set(re.findall(pattern, cleaned, re.I))
    return raw_emails

def extract_footer_emails(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    if footer:
        return extract_emails(str(footer))
    return set()

def is_valid_email(e: str) -> bool:
    try:
        if not isinstance(e, str) or '@' not in e:
            return False
        if e.lower().startswith('http') or e.lower().startswith('https'):
            return False
        user, domain = e.split('@')
        if (
            len(user) < 3 or len(domain.split('.')[0]) < 3 or
            re.search(r'\.(png|jpg|jpeg|svg|css|js|webp|html)$', e) or
            any(bad in e for bad in [
                'sentry', 'wixpress', 'cloudflare', 'gravatar', '@e.com', '@aset.', '@ar.com',
                'noreply@', 'amazonaws', 'akamai', 'doubleclick', 'pagead2.', 'googlemail',
                'wh@sapp.com', 'buyth@hotel.com'
            ]) or
            re.search(r'https?%3[a-z0-9]*@', e, re.I) or
            re.search(r'www\.', user, re.I) or
            not re.search(r'@[\w.-]+\.(com|org|net|edu|co|io)$', e, re.I)
        ):
            return False
        return True
    except Exception:
        return False

def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    outreach_keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority, others = [], []
    for email in emails:
        if any(kw in email for kw in outreach_keywords):
            priority.append(email)
        else:
            others.append(email)
    return priority, others

# --- Main Scraper Function ---
def scrape_website(start_url: str, max_count: int = 6) -> set[str] | str:
    if not start_url.startswith("http://") and not start_url.startswith("https://"):
        start_url = "https://" + start_url

    log(f"🌐 Starting scrape: {start_url}")

    base_url = get_base_url(start_url)
    urls_to_process = deque()
    scraped_urls = set()
    collected_emails = set()
    count = 0
    contact_form_found = False

    # Updated path order: prioritize /about and /about-us
    priority_paths = [
        '/contact', '/contact-us', '/write-for-us', '/guest-post', '/about', '/about-us', '/contribute',
        '/submit-guest-post', '/become-a-contributor', '/submit-post', '/editorial-guidelines'
    ]
    for path in priority_paths:
        urls_to_process.append(base_url + path)
    urls_to_process.append(start_url)

    while urls_to_process and count < max_count:
        url = urls_to_process.popleft()
        if url in scraped_urls:
            continue
        scraped_urls.add(url)
        count += 1
        page_path = get_page_path(url)

        try:
            log(f"🔍 Fetching {url}")
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            response.raise_for_status()
            html = response.text
            log(f"✅ Success [{response.status_code}] - {url}")
        except Exception as e:
            log(f"❌ Failed to fetch {url} — {str(e)}")
            continue

        emails = extract_emails(html) | extract_footer_emails(html)
        filtered = {e for e in emails if is_valid_email(e)}
        collected_emails.update(filtered)

        if not collected_emails:
            lower_html = html.lower()
            if '<form' in lower_html and any(kw in lower_html for kw in ['contact', 'write for us', 'submit', 'reach us']):
                contact_form_found = True

        soup = BeautifulSoup(html, 'lxml')
        for anchor in soup.find_all('a'):
            link = anchor.get('href', '')
            normalized = normalize_link(link, base_url, page_path)
            if any(p in normalized.lower() for p in ['write', 'guest', 'contact', 'submit', 'about']):
                if normalized not in urls_to_process and normalized not in scraped_urls:
                    urls_to_process.append(normalized)

    if collected_emails:
        priority, others = prioritize_emails(collected_emails)
        return set(priority) if priority else set(others)
    elif contact_form_found:
        return "Contact Form"
    else:
        return "No Email"
