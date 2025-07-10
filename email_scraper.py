import re
import requests
from bs4 import BeautifulSoup
from typing import Union
from playwright.async_api import async_playwright


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


def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority = [e for e in emails if any(k in e for k in keywords)]
    others = list(emails - set(priority))
    return priority, others


def filter_emails(emails: set[str]) -> set[str]:
    return {
        e for e in emails
        if not re.search(r"\.(png|jpg|jpeg|svg|css|js|webp|html)$", e)
        and not any(bad in e for bad in [
            'sentry', 'wixpress', 'cloudflare', 'gravatar', '@e.com', '@aset.', '@ar.com',
            'noreply@', 'amazonaws', 'akamai', 'doubleclick', 'pagead2.', 'googlemail',
            'wh@sapp.com', 'buyth@hotel.com'])
        and not re.search(r"https?%3[a-z0-9]*@", e, re.I)
        and not re.search(r"www\\.", e.split("@")[0], re.I)
        and not e.startswith(".") and "@" in e
        and re.search(r"@[\w.-]+\.(com|org|net|edu|co|io)$", e, re.I)
        and len(e.split("@")[1].split(".")[0]) >= 3
        and len(e.split("@")[0]) >= 3
    }


def detect_contact_form(text: str) -> bool:
    soup = BeautifulSoup(text, "lxml")
    return bool(soup.find_all("form")) and any(k in text.lower() for k in ["contact", "write for us", "submit", "reach us"])


def try_with_beautifulsoup(url: str) -> Union[set[str], str]:
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            return "No Email"

        soup = BeautifulSoup(response.text, "lxml")
        all_text = soup.get_text()
        footer = soup.find("footer")
        footer_text = str(footer) if footer else ""

        emails = extract_emails(all_text) | extract_emails(footer_text)
        emails = filter_emails(emails)

        if emails:
            priority, others = prioritize_emails(emails)
            return set(priority) if priority else emails

        if detect_contact_form(response.text):
            return "Contact Form"

        return "No Email"

    except Exception:
        return "No Email"


async def scrape_website(url: str, max_count: int = 5) -> Union[set[str], str]:
    # First try with BeautifulSoup
    bs_result = try_with_beautifulsoup(url)
    if isinstance(bs_result, set) and bs_result:
        return bs_result  # Found good emails using HTML
    if bs_result in ["Contact Form", "No Email"]:
        # Fallback to Playwright only if BS failed
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                try:
                    await page.goto(url, timeout=20000)
                    await page.wait_for_timeout(5000)
                    content = await page.content()
                    soup = BeautifulSoup(content, "lxml")

                    all_text = soup.get_text()
                    footer = soup.find("footer")
                    footer_text = str(footer) if footer else ""

                    emails = extract_emails(all_text) | extract_emails(footer_text)
                    emails = filter_emails(emails)

                    if emails:
                        priority, others = prioritize_emails(emails)
                        await browser.close()
                        return set(priority) if priority else emails

                    if detect_contact_form(content):
                        await browser.close()
                        return "Contact Form"

                    await browser.close()
                    return "No Email"

                except Exception as e:
                    await browser.close()
                    raise e

        except Exception:
            return "No Email"

    return bs_result
