from fastapi import FastAPI
from pydantic import BaseModel
from typing import Union
from bs4 import BeautifulSoup
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = FastAPI()

class ExtractRequest(BaseModel):
    url: str

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

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
    try:
        soup = BeautifulSoup(html, "lxml")
        footer = soup.find("footer")
        if footer:
            return extract_emails(str(footer))
    except Exception:
        pass
    return set()

def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority = [e for e in emails if any(k in e for k in keywords)]
    others = list(emails - set(priority))
    return priority, others

def filter_emails(emails: set[str]) -> set[str]:
    filtered = set()
    for e in emails:
        try:
            user_domain = e.split('@')
            if len(user_domain) != 2:
                continue
            username, domain_part = user_domain
            domain_main = domain_part.split('.')[0]
            if (
                re.search(r"\.(png|jpg|jpeg|svg|css|js|webp|html)$", e) or
                any(bad in e for bad in [
                    'sentry', 'wixpress', 'cloudflare', 'gravatar', '@e.com', '@aset.', '@ar.com',
                    'noreply@', 'amazonaws', 'akamai', 'doubleclick', 'pagead2.', 'googlemail',
                    'wh@sapp.com', 'buyth@hotel.com'
                ]) or
                re.search(r"https?%3[a-z0-9]*@", e, re.I) or
                re.search(r"www\.", username, re.I) or
                e.startswith(".") or
                '@' not in e or
                not re.search(r"@[\w.-]+\.(com|org|net|edu|co|io)$", e, re.I) or
                len(domain_main) < 3 or
                len(username) < 3
            ):
                continue
            filtered.add(e)
        except Exception:
            continue
    return filtered

@app.post("/extract")
async def extract_email(request: ExtractRequest):
    try:
        driver = create_driver()
        driver.get(request.url)
        time.sleep(6)
        html = driver.page_source
        driver.quit()

        emails_all = extract_emails(html)
        emails_footer = extract_footer_emails(html)
        combined = emails_all | emails_footer

        filtered = filter_emails(combined)

        if filtered:
            priority, others = prioritize_emails(filtered)
            return {
                "email": priority[0] if priority else next(iter(filtered)),
                "emails": sorted(filtered)
            }

        if "form" in html.lower() and any(k in html.lower() for k in ['contact', 'write for us', 'submit']):
            return "Contact Form"
        return "No Email"

    except Exception as e:
        return {"error": str(e)}
