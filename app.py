import requests
from bs4 import BeautifulSoup
import re

def clean_text(text):
    text = text.lower()
    text = text.replace('[at]', '@').replace('(at)', '@').replace(' at ', '@')
    text = text.replace('[dot]', '.').replace('(dot)', '.').replace(' dot ', '.')
    text = text.replace('[@]', '@').replace('[.]', '.')
    return text

def extract_emails_from_text(text):
    text = clean_text(text)
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))

def extract_emails_from_url(url):
    pages_to_check = ['', '/contact', '/about', '/privacy']

    for page in pages_to_check:
        full_url = url if url.startswith("http") else f"https://{url}"
        if not full_url.endswith(page):
            full_url = full_url.rstrip('/') + page
        try:
            resp = requests.get(full_url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                text = soup.get_text()
                emails = extract_emails_from_text(text)
                if emails:
                    return emails, full_url
        except:
            continue

    return [], None
