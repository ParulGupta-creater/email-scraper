from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Union
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlsplit, urljoin
import time

app = FastAPI()

class InputURL(BaseModel):
    url: str

def get_headless_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

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

def prioritize_emails(emails: set[str]) -> list[str]:
    outreach_keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority = [e for e in emails if any(kw in e for kw in outreach_keywords)]
    return priority if priority else list(emails)

def is_valid_email(email: str) -> bool:
    if not email or '@' not in email:
        return False
    username, domain = email.split('@')
    if len(username) < 3 or len(domain.split('.')[0]) < 3:
        return False
    if re.search(r'https?%3[a-z0-9]*@', email, re.I):
        return False
    if re.search(r'www\.', username, re.I):
        return False
    if re.search(r'\.(png|jpg|jpeg|svg|css|js|webp|html)$', email):
        return False
    bad_keywords = ['sentry', 'wixpress', 'cloudflare', 'gravatar', '@e.com', '@aset.', '@ar.com',
                    'noreply@', 'amazonaws', 'akamai', 'doubleclick', 'pagead2.', 'googlemail',
                    'wh@sapp.com', 'buyth@hotel.com']
    return not any(bad in email for bad in bad_keywords)

def get_base_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"

@app.post("/extract")
async def extract(input: InputURL):
    try:
        url = input.url.strip().lower()
        base_url = get_base_url(url)
        visited = set()
        all_emails = set()
        priority_links = [
            url,
            urljoin(base_url, "/contact"),
            urljoin(base_url, "/write-for-us"),
            urljoin(base_url, "/guest-post"),
            urljoin(base_url, "/submit"),
        ]

        browser = get_headless_browser()

        for link in priority_links[:5]:
            if link in visited:
                continue
            visited.add(link)
            try:
                browser.get(link)
                time.sleep(3)
                html = browser.page_source
                soup = BeautifulSoup(html, 'lxml')

                # All text
                all_emails.update(extract_emails(html))

                # Footer emails
                footer = soup.find("footer")
                if footer:
                    all_emails.update(extract_emails(str(footer)))

                # Explore more contact links on first page
                if link == url:
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if any(kw in href.lower() for kw in ['contact', 'guest', 'write', 'submit']):
                            abs_link = urljoin(base_url, href)
                            if abs_link not in visited:
                                priority_links.append(abs_link)

            except Exception as e:
                continue

        browser.quit()

        filtered_emails = {e for e in all_emails if is_valid_email(e)}
        prioritized = prioritize_emails(filtered_emails)

        if prioritized:
            return {
                "email": prioritized[0],
                "emails": list(filtered_emails)
            }

        if "<form" in html.lower() and any(k in html.lower() for k in ["contact", "write", "submit", "reach us"]):
            return {"email": "Contact Form", "emails": []}

        return {"email": "No Email", "emails": []}

    except Exception as e:
        return {"error": str(e)}
