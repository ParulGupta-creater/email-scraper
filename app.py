from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
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
        result = scrape_website(request.url, max_count=5)  # reduced count

        if isinstance(result, set):
            emails = list(result)
            return {
                "email": emails[0] if emails else None,
                "emails": emails
            }
        else:
            return {
                "email": result,
                "emails": []
            }

    except Exception as e:
        return {"error": str(e)}

# ✅ Endpoint for scraping multiple URLs
@app.post("/extract-batch")
def extract_emails_batch(request: BatchURLRequest):
    results = []
    for url in request.urls:
        try:
            result = scrape_website(url, max_count=2)

            if isinstance(result, set):
                emails = list(result)
                results.append({
                    "url": url,
                    "email": emails[0] if emails else None,
                    "all_emails": emails
                })
            else:
                results.append({
                    "url": url,
                    "email": result,
                    "all_emails": []
                })

        except Exception as e:
            results.append({
                "url": url,
                "error": str(e),
                "email": None,
                "all_emails": []
            })

    return results
