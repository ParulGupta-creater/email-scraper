import re
import time
import urllib.parse
from collections import deque
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Helper: Normalize base URL
def get_base_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f'{parts.scheme}://{parts.netloc}'

# Helper: Page path for relative links
def get_page_path(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return url[:url.rfind('/') + 1] if '/' in parts.path else url

# Helper: Normalize hrefs
def normalize_link(link: str, base_url: str, page_path: str) -> str:
    if not link:
        return ""
    link = link.strip()
    if link.startswith('//'):
        return 'https:' + link
    elif link.startswith('/'):
        return base_url + link
    elif not link.startswith('http'):
        return urllib.parse.urljoin(page_path, link)
    return link

# Clean and deobfuscate text for email patterns
def clean_text(text: str) -> str:
    # Common obfuscations
    patterns = {
        r'\s?\[at\]\s?': '@', r'\s?\(at\)\s?': '@', r'\s+at\s+': '@',
        r'\s?\[dot\]\s?': '.', r'\s?\(dot\)\s?': '.', r'\s+dot\s+': '.',
        r'\s?\[\s?at\s?\]\s?': '@', r'\s?\[\s?dot\s?\]\s?': '.',
        r'\s?\[?\s*at\s*\]?\s?': '@', r'\s?\[?\s*dot\s*\]?\s?': '.',
        r'\s?{at}\s?': '@', r'\s?{dot}\s?': '.',
        r'\s?&#64;\s?': '@', r'\s?&#46;\s?': '.',
        r'\s?&lt;\s?': '<', r'\s?&gt;\s?': '>',
        r'\s?\[~at~\]\s?': '@', r'\s?\[~dot~\]\s?': '.',
        r'\s?\[email protected\]\s?': '@',
    }
    text = text.lower()
    for pat, rep in patterns.items():
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)
    # Remove spaces within emails e.g. "jane @ example . com"
    text = re.sub(r'(\w)\s*@\s*(\w)', r'\1@\2', text)
    text = re.sub(r'(\w)\s*\.\s*(\w)', r'\1.\2', text)
    return text

# Extract emails from HTML/text
def extract_emails(text: str) -> set[str]:
    cleaned = clean_text(text)
    # Standard email regex, plus handle unicode @ and .
    email_regex = r'[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}'
    return set(re.findall(email_regex, cleaned, re.I))

# Extract emails from <footer>
def extract_footer_emails(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    if footer:
        return extract_emails(str(footer))
    return set()

# Attempt to extract email from mailto: links
def extract_mailto_emails(soup) -> set[str]:
    emails = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().startswith('mailto:'):
            email = href[7:]
            if '?' in email:
                email = email.split('?', 1)[0]
            email = clean_text(email)
            if '@' in email:
                emails.add(email)
    return emails

# Prioritize outreach emails
def prioritize_emails(emails: set[str]) -> tuple[list[str], list[str]]:
    outreach_keywords = ['editor', 'contact', 'info', 'submit', 'guest', 'write', 'pitch', 'tip', 'team']
    priority, others = [], []
    for email in emails:
        if any(kw in email for kw in outreach_keywords):
            priority.append(email)
        else:
            others.append(email)
    return priority, others

# Detect if a contact form exists
def has_contact_form(soup) -> bool:
    form = soup.find('form')
    if form:
        form_html = str(form).lower()
        keywords = ['contact', 'write', 'submit', 'reach', 'message', 'enquiry', 'feedback', 'support', 'join']
        if any(kw in form_html for kw in keywords):
            return True
    return False

# Main scraping logic
def scrape_website(start_url: str, max_pages: int = 5, delay: float = 1.5, verbose: bool = False) -> set[str] | str:
    base_url = get_base_url(start_url)
    urls_to_process = deque()
    scraped_urls = set()
    collected_emails = set()
    contact_form_found = False

    # Headless browser setup
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1200")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=chrome_options)

    # High priority subpages
    priority_paths = [
        '/contact', '/contact-us', '/write-for-us', '/guest-post', '/contribute',
        '/submit-guest-post', '/become-a-contributor', '/submit-post', '/editorial-guidelines'
    ]
    for path in priority_paths:
        urls_to_process.append(base_url + path)
    urls_to_process.append(start_url)  # homepage last

    pages_visited = 0
    while urls_to_process and pages_visited < max_pages:
        url = urls_to_process.popleft()
        if url in scraped_urls:
            continue
        scraped_urls.add(url)
        pages_visited += 1
        page_path = get_page_path(url)

        try:
            driver.get(url)
            time.sleep(delay)  # let JS load
            html = driver.page_source
        except Exception as e:
            if verbose:
                print(f"[WARN] Could not load {url}: {e}")
            continue

        soup = BeautifulSoup(html, "lxml")

        # Extract emails from page and footer and mailto links
        emails = extract_emails(html)
        emails |= extract_footer_emails(html)
        emails |= extract_mailto_emails(soup)

        # Filter out junk
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
        if verbose and emails:
            print(f"[DEBUG] {url}: found emails: {emails}")
        if verbose and filtered != emails:
            print(f"[DEBUG] {url}: filtered emails: {filtered}")

        collected_emails.update(filtered)

        # If no emails, check for contact form signals
        if not collected_emails and has_contact_form(soup):
            contact_form_found = True

        # Discover more relevant links
        for anchor in soup.find_all('a', href=True):
            link = anchor['href']
            normalized = normalize_link(link, base_url, page_path)
            # Only follow links on same domain and not already queued/visited
            if normalized.startswith(base_url) and normalized not in urls_to_process and normalized not in scraped_urls:
                if any(p in normalized.lower() for p in ['contact', 'write', 'guest', 'submit', 'about', 'editor']):
                    urls_to_process.append(normalized)

    driver.quit()

    # Return best match
    if collected_emails:
        priority, others = prioritize_emails(collected_emails)
        return set(priority) if priority else set(others)
    elif contact_form_found:
        return "Contact Form"
    else:
        return "No Email"

# Example usage:
if __name__ == "__main__":
    url = input("Enter website URL: ")
    emails = scrape_website(url, verbose=True)
    print("Result:", emails)
