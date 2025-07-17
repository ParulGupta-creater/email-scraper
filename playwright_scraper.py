import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# --- Email Cleaning & Extraction Logic ---

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

def extract_emails(html: str) -> set[str]:
    cleaned = clean_text(html)
    pattern = r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}'
    return set(re.findall(pattern, cleaned, re.I))

def is_valid_email(e: str) -> bool:
    try:
        if not isinstance(e, str) or '@' not in e:
            return False
        user, domain = e.split('@')
        if (
            len(user) < 3 or len(domain.split('.')[0]) < 3 or
            re.search(r'\.(png|jpg|jpeg|svg|css|js|webp|html)$', e) or
            any(bad in e for bad in [
                'sentry', 'wixpress', 'cloudflare', 'gravatar', '@e.com', '@aset.', '@ar.com',
                'noreply@', 'amazonaws', 'akamai', 'doubleclick', 'pagead2.', 'googlemail',
                'wh@sapp.com', 'buyth@hotel.com'
            ]) or
            re.search(r'https?%3[a-z0-9]*@', e, re.I) or
            re.search(r'www\.', user, re.I) or
            not re.search(r'@[\w.-]+\.(com|org|net|edu|co|io)$', e, re.I)
        ):
            return False
        return True
    except Exception:
        return False

def filter_emails(emails: set[str]) -> set[str]:
    return {e for e in emails if is_valid_email(e)}

def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    outreach_keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority, others = [], []
    for email in emails:
        if any(kw in email for kw in outreach_keywords):
            priority.append(email)
        else:
            others.append(email)
    return priority, others

def detect_contact_form(html: str) -> bool:
    lower_html = html.lower()
    return '<form' in lower_html and any(kw in lower_html for kw in ['contact', 'write for us', 'submit', 'reach us'])

# --- Main Scraper Function ---

async def scrape_with_playwright(url: str) -> set[str] | str:
    browser = None
    try:
        if not url.startswith("http"):
            url = "https://" + url

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = await browser.new_page()
            await page.goto(url, timeout=20000)
            await page.wait_for_timeout(5000)

            content = await page.content()
            soup = BeautifulSoup(content, "lxml")
            text = soup.get_text()
            footer = soup.find("footer")
            footer_text = str(footer) if footer else ""

            emails = extract_emails(text) | extract_emails(footer_text)
            emails = filter_emails(emails)

            if emails:
                priority, others = prioritize_emails(emails)
                return set(priority) if priority else emails

            if detect_contact_form(content):
                return "Contact Form"

            return "No Email"

    except Exception as e:
        print(f"❌ Playwright failed: {e}")
        return "No Email"
    finally:
        if browser:
            await browser.close()
