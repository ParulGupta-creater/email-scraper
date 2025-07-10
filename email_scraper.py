import re
import requests
from bs4 import BeautifulSoup
from typing import Union, Set
import asyncio
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


def extract_emails(text: str) -> Set[str]:
    cleaned = clean_text(text)
    return set(re.findall(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", cleaned, re.I))


def filter_emails(emails: Set[str]) -> Set[str]:
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


def prioritize_emails(emails: Set[str]) -> tuple[list[str], list[str]]:
    keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority = [e for e in emails if any(k in e for k in keywords)]
    others = list(emails - set(priority))
    return priority, others


def try_static_scrape(url: str) -> Union[Set[str], None]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        all_text = soup.get_text()
        footer = soup.find("footer")
        footer_text = str(footer) if footer else ""

        emails = extract_emails(all_text) | extract_emails(footer_text)
        return filter_emails(emails)
    except Exception:
        return None


async def scrape_with_playwright(url: str, max_count: int = 5) -> Union[Set[str], str]:
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

            if "form" in content.lower() and any(k in content.lower() for k in ['contact', 'write for us', 'submit']):
                await browser.close()
                return "Contact Form"

            await browser.close()
            return "No Email"

        except Exception as e:
            await browser.close()
            raise e


async def scrape_website(url: str, max_count: int = 5) -> Union[Set[str], str]:
    static_emails = try_static_scrape(url)
    if static_emails:
        priority, others = prioritize_emails(static_emails)
        return set(priority) if priority else static_emails

    return await scrape_with_playwright(url, max_count)
