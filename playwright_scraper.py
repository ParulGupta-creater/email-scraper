import re
from bs4 import BeautifulSoup
from typing import Union, Set
from playwright.async_api import async_playwright
from beautifulsoup_scraper import clean_text, extract_emails, filter_emails, prioritize_emails, detect_contact_form


async def scrape_with_playwright(url: str) -> Union[Set[str], str]:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=20000)
            await page.wait_for_timeout(5000)
            content = await page.content()

            soup = BeautifulSoup(content, "lxml")
            all_text = soup.get_text()
            footer = soup.find("footer")
            footer_text = str(footer) if footer else ""

            emails = extract_emails(all_text) | extract_emails(footer_text)
            emails = filter_emails(emails)

            await browser.close()

            if emails:
                priority, others = prioritize_emails(emails)
                return set(priority) if priority else emails

            if detect_contact_form(content):
                return "Contact Form"

            return "No Email"

    except Exception:
        return "No Email"
