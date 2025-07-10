from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re
import time
import urllib.parse
from collections import deque

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

def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def clean_text(text: str) -> str:
    text = text.lower()
    replacements = {
        r"\[at\]": "@", r"\(at\)": "@", r"\s+at\s+": "@",
        r"\[dot\]": ".", r"\(dot\)": ".", r"\s+dot\s+": ".",
        r"\[@\]": "@", r"\[\.\]": ".", r"\s*\[?\s*at\s*\]?\s*": "@",
        r"\s*\[?\s*dot\s*\]?\s*": ".",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def extract_emails(text: str) -> set[str]:
    cleaned = clean_text(text)
    return set(re.findall(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", cleaned, re.I))

def extract_footer_emails(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    if footer:
        return extract_emails(str(footer))
    return set()

def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority = [e for e in emails if any(k in e for k in keywords)]
    others = list(emails - set(priority))
    return priority, others

def is_valid_email(e: str) -> bool:
    if not e or "@" not in e:
        return False
    try:
        user, domain = e.split("@")
        domain_parts = domain.split(".")
        return (
            len(user) >= 3 and
            len(domain_parts[0]) >= 3 and
            re.search(r"@[\w.-]+\.(com|org|net|edu|co|io)$", e, re.I) and
            not re.search(r"\.(png|jpg|jpeg|svg|css|js|webp|html)$", e) and
            not any(bad in e for bad in [
                'sentry', 'wixpress', 'cloudflare', 'gravatar', '@e.com', '@aset.', '@ar.com',
                'noreply@', 'amazonaws', 'akamai', 'doubleclick', 'pagead2.', 'googlemail',
                'wh@sapp.com', 'buyth@hotel.com'
            ]) and
            not re.search(r"https?%3[a-z0-9]*@", e, re.I) and
            not re.search(r"www\.", user, re.I) and
            not e.startswith(".")
        )
    except Exception:
        return False

def filter_emails(emails: set[str]) -> set[str]:
    return {e for e in emails if is_valid_email(e)}

def scrape_website(start_url: str, max_count: int = 5) -> set[str] | str:
    base_url = get_base_url(start_url)
    urls_to_process = deque()
    scraped_urls = set()
    collected_emails = set()
    contact_form_found = False

    priority_paths = [
        '/contact', '/contact-us', '/write-for-us', '/guest-post', '/contribute',
        '/submit-guest-post', '/become-a-contributor', '/submit-post', '/editorial-guidelines'
    ]
    for path in priority_paths:
        urls_to_process.append(base_url + path)
    urls_to_process.append(start_url)

    driver = create_driver()

    try:
        while urls_to_process and len(scraped_urls) < max_count:
            url = urls_to_process.popleft()
            if url in scraped_urls:
                continue

            scraped_urls.add(url)
            driver.get(url)
            time.sleep(5)
            html = driver.page_source
            page_path = get_page_path(url)

            emails = extract_emails(html) | extract_footer_emails(html)
            filtered = filter_emails(emails)
            collected_emails.update(filtered)

            if not filtered:
                lower_html = html.lower()
                if '<form' in lower_html and any(k in lower_html for k in ['contact', 'write for us', 'submit']):
                    contact_form_found = True

            soup = BeautifulSoup(html, 'lxml')
            for anchor in soup.find_all('a'):
                link = anchor.get('href', '')
                normalized = normalize_link(link, base_url, page_path)
                if any(p in normalized.lower() for p in ['write', 'guest', 'contact', 'submit']):
                    if normalized not in urls_to_process and normalized not in scraped_urls:
                        urls_to_process.append(normalized)

    finally:
        driver.quit()

    if collected_emails:
        priority, others = prioritize_emails(collected_emails)
        return set(priority) if priority else set(others)
    elif contact_form_found:
        return "Contact Form"
    else:
        return "No Email"
