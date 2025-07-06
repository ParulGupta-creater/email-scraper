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

def extract_emails_from_html(html: str) -> set[str]:
    """Extracts emails from the entire HTML."""
    return extract_emails(html)

def extract_emails_from_footer(html: str) -> set[str]:
    """Extracts emails specifically from the <footer> tag if present."""
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    if footer:
        footer_text = str(footer)
        return extract_emails(footer_text)
    return set()

def prioritize_emails(emails):
    outreach_keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip']
    priority = []
    others = []
    for email in emails:
        if any(kw in email for kw in outreach_keywords):
            priority.append(email)
        else:
            others.append(email)
    return priority, others

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

        page_html = response.text

        # 1. Extract emails from full HTML
        raw_emails = extract_emails_from_html(page_html)
        # 2. Extract emails specifically from footer
        footer_emails = extract_emails_from_footer(page_html)

        # 3. Combine and filter emails
        all_emails = raw_emails | footer_emails

        # Filtering: remove image, script, etc. false positives, but don't require special keywords
        filtered_emails = {
            email for email in all_emails
            if not re.search(r'\.(webp|png|jpg|jpeg|html|css|svg|js)$', email)
            and not any(bad in email for bad in [
                'googlesyndication.com', 'ads.', '@ion.', '@ung.', '@boden.',
                'alayer.push', 'templ@e.', 'block-post', 'author@', 'team@'
            ])
            and not email.startswith('.')
            and re.search(r'@[\w.-]+\.(com|org|net|edu|co|io)', email, re.I)
            and len(email.split('@')[1].split('.')[0]) >= 3
        }

        collected_emails.update(filtered_emails)

        # 4. Check for contact form (but don't return early—always prefer emails if any found)
        text = page_html.lower()
        if (
            '<form' in text and
            any(keyword in text for keyword in ['contact', 'write for us', 'submit a guest post', 'contribute'])
        ):
            contact_form_found = True

        # 5. Continue following relevant links
        soup = BeautifulSoup(page_html, 'lxml')
        for anchor in soup.find_all('a'):
            link = anchor.get('href', '')
            normalized_link = normalize_link(link, base_url, page_path)
            if any(p in normalized_link.lower() for p in ['write', 'guest', 'contact', 'submit']):
                if normalized_link not in urls_to_process and normalized_link not in scraped_urls:
                    urls_to_process.append(normalized_link)

    # FINAL DECISION: Always prefer emails over contact form, prefer outreach emails if found
    if collected_emails:
        priority, others = prioritize_emails(collected_emails)
        return set(priority) if priority else set(others)
    elif contact_form_found:
        return "Contact Form"
    else:
        return "No Email"
