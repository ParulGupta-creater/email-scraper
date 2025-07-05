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

# ✅ Main scraping function
def scrape_website(start_url: str, max_count: int = 3) -> set[str] | str:
    base_url = get_base_url(start_url)
    urls_to_process = deque()
    scraped_urls = set()
    collected_emails = set()
    count = 0
    contact_form_found = False

    # ✅ High-priority pages for guest posts
    priority_paths = [
        '/contact', '/contact-us', '/write-for-us', '/guest-post',
        '/contribute', '/submit-guest-post', '/become-a-contributor',
        '/submit-post', '/editorial-guidelines'
    ]
    for path in priority_paths:
        urls_to_process.append(base_url + path)

    # Fallback: add homepage last
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

        raw_emails = extract_emails(response.text)

        # ✅ Filter: keep only likely guest post-related emails
        filtered_emails = {
            email for email in raw_emails
            if not re.search(r'\.(webp|png|jpg|jpeg|html|css|svg|js)$', email)
            and not any(bad in email for bad in [
                'googlesyndication.com', 'ads.', '@ion.', '@ung.', '@boden.',
                'alayer.push', 'templ@e.', 'block-post', 'author@', 'team@'
            ])
            and not email.startswith('.')
            and re.search(r'@[\w.-]+\.(com|org|net|edu|co|io)', email, re.I)
            and len(email.split('@')[1].split('.')[0]) >= 3
            and any(kw in email for kw in ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip'])
        }

        collected_emails.update(filtered_emails)

        if not collected_emails:
            text = response.text.lower()
            if (
                '<form' in text and
                any(keyword in text for keyword in ['contact', 'write for us', 'submit a guest post', 'contribute'])
            ):
                contact_form_found = True

        # 🧠 Optional: follow relevant new links
        soup = BeautifulSoup(response.text, 'lxml')
        for anchor in soup.find_all('a'):
            link = anchor.get('href', '')
            normalized_link = normalize_link(link, base_url, page_path)
            if any(p in normalized_link.lower() for p in ['write', 'guest', 'contact', 'submit']):
                if normalized_link not in urls_to_process and normalized_link not in scraped_urls:
                    urls_to_process.append(normalized_link)

    if collected_emails:
        return collected_emails
    elif contact_form_found:
        return "Contact Form"
    else:
        return "No Email"
