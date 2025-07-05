from collections import deque
import urllib.parse
import re
from bs4 import BeautifulSoup
import requests
import requests.exceptions as request_exception

def get_base_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return '{0.scheme}://{0.netloc}'.format(parts)

def get_page_path(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return url[:url.rfind('/') + 1] if '/' in parts.path else url

def clean_text(text: str) -> str:
    text = text.lower()
    obfuscations = {
        r'\[at\]': '@',
        r'\(at\)': '@',
        r'\s+at\s+': '@',
        r'\[dot\]': '.',
        r'\(dot\)': '.',
        r'\s+dot\s+': '.',
        r'\[@\]': '@',
        r'\[\.\]': '.',
        r'\s*\[?\s*at\s*\]?\s*': '@',
        r'\s*\[?\s*dot\s*\]?\s*': '.',
    }

    for pattern, replacement in obfuscations.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text

def extract_emails(response_text: str) -> set[str]:
    cleaned_text = clean_text(response_text)
    email_pattern = r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}'
    return set(re.findall(email_pattern, cleaned_text, re.I))

def normalize_link(link: str, base_url: str, page_path: str) -> str:
    if link.startswith('/'):
        return base_url + link
    elif not link.startswith('http'):
        return page_path + link
    return link

def scrape_website(start_url: str, max_count: int = 100) -> set[str]:
    urls_to_process = deque([start_url])
    scraped_urls = set()
    collected_emails = set()
    count = 0

    while urls_to_process:
        count += 1
        if count > max_count:
            break

        url = urls_to_process.popleft()
        if url in scraped_urls:
            continue

        scraped_urls.add(url)
        base_url = get_base_url(url)
        page_path = get_page_path(url)

        print(f'[{count}] Processing {url}')

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except (request_exception.RequestException, request_exception.MissingSchema, request_exception.ConnectionError):
            print('There was a request error')
            continue

        # Extract and filter emails
raw_emails = extract_emails(response.text)
filtered_emails = {
    email for email in raw_emails
    if not re.search(r'\.(webp|png|jpg|jpeg|html|css|svg|js)$', email)
    and not any(domain in email for domain in ['googlesyndication.com', 'ads.', '@ion.', '@ung.', '@boden.'])
}
collected_emails.update(filtered_emails)


        soup = BeautifulSoup(response.text, 'lxml')

        for anchor in soup.find_all('a'):
            link = anchor.get('href', '')
            normalized_link = normalize_link(link, base_url, page_path)
            if normalized_link not in urls_to_process and normalized_link not in scraped_urls:
                urls_to_process.append(normalized_link)

    return collected_emails

# ✅ CLI Entry point - safe for Render (only runs if executed manually)
if __name__ == "__main__":
    try:
        user_url = input('[+] Enter url to scan: ')
        emails = scrape_website(user_url)

        if emails:
            print('\n[+] Found emails:')
            for email in emails:
                print(email)
        else:
            print('[-] No emails found.')
    except KeyboardInterrupt:
        print('[-] Closing!')
