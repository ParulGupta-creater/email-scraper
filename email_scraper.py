from collections import deque
import urllib.parse
import re
from bs4 import BeautifulSoup
import requests
import requests.exceptions as request_exception

# 🧩 Helper functions
def get_base_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return '{0.scheme}://{0.netloc}'.format(parts)

def get_page_path(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return url[:url.rfind('/') + 1] if '/' in parts.path else url

def normalize_link(link: str, base_url: str, page_path: str) -> str:
    if link.startswith('/'):
        return base_url + link
    elif not link.startswith('http'):
        return page_path + link
    return link

# ✅ Clean and extract emails from page text
def clean_text(text: str) -> str:
    text = text.lower()
    obfuscations = {
        r'\[at\]': '@',
        r'\(at\)': '@',
        r'\s+at\s+': '@',
        r'\[dot\]': '.',
        r'\(dot\)': '.',
        r'\s+dot\s+': '.',
        r'\[@\]': '@',
        r'\[\.\]': '.',
        r'\s*\[?\s*at\s*\]?\s*': '@',
        r'\s*\[?\s*dot\s*\]?\s*': '.',
    }
    for pattern, replacement in obfuscations.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def extract_emails(response_text: str) -> set[str]:
    cleaned_text = clean_text(response_text)
    email_pattern = r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}'
    return set(re.findall(email_pattern, cleaned_text, re.I))

# ✅ Main scraping function (updated for 4-page limit and prioritization)
def scrape_website(start_url: str, max_count: int = 2) -> set[str] | str:
    base_url = get_base_url(start_url)
    urls_to_process = deque()
    scraped_urls = set()
    collected_emails = set()
    count = 0
    contact_form_found = False

    # First add important pages like /contact, /about, etc.
    priority_paths = ['/contact', '/about', '/privacy', '/team', '/impressum']
    for path in priority_paths:
        priority_url = base_url + path
        urls_to_process.append(priority_url)

    # Then add the homepage last to be processed after priority pages
    urls_to_process.append(start_url)

    while urls_to_process:
        if count >= max_count:
            break

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

        # ✅ Extract and filter emails
        raw_emails = extract_emails(response.text)
        filtered_emails = {
            email for email in raw_emails
            if not re.search(r'\.(webp|png|jpg|jpeg|html|css|svg|js)$', email)
            and not any(bad in email for bad in [
                'googlesyndication.com', 'ads.', '@ion.', '@ung.', '@boden.',
                'alayer.push', 'templ@e.', 'block-post'
            ])
            and not email.startswith('.')
            and re.search(r'@[\w.-]+\.(com|org|net|edu|co|io)', email, re.I)
            and len(email.split('@')[1].split('.')[0]) >= 3
        }

        collected_emails.update(filtered_emails)

        # ✅ Check for contact form
        if not collected_emails:
            text = response.text.lower()
            if (
                '<form' in text and
                any(keyword in text for keyword in ['contact', 'get in touch', 'reach us', 'enquiry'])
            ):
                contact_form_found = True

        # ✅ Discover more links (within max page visit limit)
        soup = BeautifulSoup(response.text, 'lxml')
        for anchor in soup.find_all('a'):
            link = anchor.get('href', '')
            normalized_link = normalize_link(link, base_url, page_path)
            if normalized_link not in urls_to_process and normalized_link not in scraped_urls:
                urls_to_process.append(normalized_link)

    if collected_emails:
        return collected_emails
    elif contact_form_found:
        return "Contact Form"
    else:
        return "No Email"
