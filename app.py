from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from email_scraper import scrape_website

app = FastAPI()

# ✅ Single URL request model
class URLRequest(BaseModel):
    url: str

# ✅ Batch URL request model
class BatchURLRequest(BaseModel):
    urls: List[str]

@app.get("/")
def root():
    return {"message": "Email Scraper API is running"}

# ✅ Endpoint for scraping a single URL
@app.post("/extract")
def extract_emails(request: URLRequest):
    try:
        emails = scrape_website(request.url, max_count=20)
        return {
            "email": list(emails)[0] if emails else None,
            "emails": list(emails),
        }
    except Exception as e:
        return {"error": str(e)}

# ✅ Endpoint for scraping multiple URLs
@app.post("/extract-batch")
def extract_emails_batch(request: BatchURLRequest):
    results = []
    for url in request.urls:
        try:
            emails = scrape_website(url, max_count=20)
            valid_email = next(iter(emails), None)
            results.append({
                "url": url,
                "email": valid_email,
                "all_emails": list(emails)
            })
        except Exception as e:
            results.append({
                "url": url,
                "error": str(e),
                "email": None,
                "all_emails": []
            })
    return results
