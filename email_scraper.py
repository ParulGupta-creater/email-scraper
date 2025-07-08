from fastapi import FastAPI, Request
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

# Request model
class ExtractRequest(BaseModel):
    url: str

# Setup headless Selenium driver
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

# Clean text to handle obfuscated email formats
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

# Extract emails using regex
def extract_emails(text: str) -> set[str]:
    cleaned = clean_text(text)
    return set(re.findall(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", cleaned, re.I))

# Extract footer emails
def extract_footer_emails(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    if footer:
        return extract_emails(str(footer))
    return set()

# Prioritize guest-posting related emails
def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority = [e for e in emails if any(k in e for k in keywords)]
    others = list(emails - set(priority))
    return priority, others

# Email filtering rules
def filter_emails(emails: set[str]) -> set[str]:
    filtered = {
        e for e in emails
        if not re.search(r"\.(png|jpg|jpeg|svg|css|js|webp|html)$", e)
        and not any(bad in e for bad in [
            'sentry', 'wixpress', 'cloudflare', 'gravatar', '@e.com', '@aset.', '@ar.com',
            'noreply@', 'amazonaws', 'akamai', 'doubleclick', 'pagead2.', 'googlemail',
            'wh@sapp.com', 'buyth@hotel.com'
        ])
        and not re.search(r"https?%3[a-z0-9]*@", e, re.I)
        and not re.search(r"www\.", e.split("@")[0], re.I)
        and not e.startswith(".") and "@" in e
        and re.search(r"@[\w.-]+\.(com|org|net|edu|co|io)$", e, re.I)
        and len(e.split("@")[1].split(".")[0]) >= 3
        and len(e.split("@")[0]) >= 3
    }
    return filtered

@app.post("/extract")
async def extract_email(request: ExtractRequest):
    try:
        driver = create_driver()
        driver.get(request.url)
        time.sleep(6)  # Allow JS to load
        html = driver.page_source
        driver.quit()

        emails = extract_emails(html) | extract_footer_emails(html)
        filtered = filter_emails(emails)

        if filtered:
            priority, others = prioritize_emails(filtered)
            return {
                "email": priority[0] if priority else next(iter(filtered)),
                "emails": sorted(filtered)
            }

        # Look for contact form if no email
        if "form" in html.lower() and any(k in html.lower() for k in ['contact', 'write for us', 'submit']):
            return "Contact Form"
        return "No Email"

    except Exception as e:
        return {"error": str(e)}
