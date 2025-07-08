from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Union
from collections import deque
import re
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def get_base_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"

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
    pattern = r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}'
    return set(re.findall(pattern, cleaned, re.I))

def extract_footer_emails(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    if footer:
        return extract_emails(str(footer))
    return set()

def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    outreach_keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority, others = [], []
    for email in emails:
        if any(kw in email for kw in outreach_keywords):
            priority.append(email)
        else:
            others.append(email)
    return priority, others

def scrape_website(start_url: str, max_count: int = 5) -> Union[set[str], str]:
    driver = get_driver()
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

    count = 0
    try:
        while urls_to_process and count < max_count:
            url = urls_to_process.popleft()
            if url in scraped_urls:
                continue
            scraped_urls.add(url)
            count += 1
            page_path = get_page_path(url)

            try:
                driver.get(url)
                html = driver.page_source
            except Exception:
                continue

            emails = extract_emails(html) | extract_footer_emails(html)

            filtered = {
                e for e in emails
                if not re.search(r'\.(png|jpg|jpeg|svg|css|js|webp|html)$', e)
                and not any(bad in e for bad in [
                    'sentry', 'wixpress', 'cloudflare', 'gravatar', '@e.com', '@aset.', '@ar.com',
                    'noreply@', 'amazonaws', 'akamai', 'doubleclick', 'pagead2.', 'googlemail',
                    'wh@sapp.com', 'buyth@hotel.com'
                ])
                and not re.search(r'https?%3[a-z0-9]*@', e, re.I)
                and not re.search(r'www\.', e.split('@')[0], re.I)
                and not e.startswith('.') and '@' in e
                and re.search(r'@[\w.-]+\.(com|org|net|edu|co|io)$', e, re.I)
                and len(e.split('@')[1].split('.')[0]) >= 3
                and len(e.split('@')[0]) >= 3
            }

            collected_emails.update(filtered)

            if not collected_emails:
                if '<form' in html.lower() and any(kw in html.lower() for kw in ['contact', 'write for us', 'submit', 'reach us']):
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

@app.post("/extract")
def extract_emails_endpoint(payload: ScrapeRequest):
    result = scrape_website(payload.url)
    if isinstance(result, str):
        return {"email": result, "emails": []}
    else:
        emails = list(result)
        return {"email": emails[0] if emails else "", "emails": emails}

