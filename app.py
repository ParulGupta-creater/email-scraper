from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
from email_scraper import scrape_website

app = FastAPI()

class URLRequest(BaseModel):
    url: str

class BatchURLRequest(BaseModel):
    urls: List[str]

@app.get("/")
def root():
    return {"message": "✅ Email Scraper API is running"}

@app.post("/extract")
async def extract_emails(request: URLRequest):
    try:
        result = await scrape_website(request.url, max_count=2)

        if isinstance(result, set):
            emails = list(result)
            return {
                "email": emails[0] if emails else None,
                "emails": emails
            }
        elif isinstance(result, str):  # e.g. "Contact Form" or "No Email"
            return {
                "email": result,
                "emails": []
            }
        else:
            return {
                "email": None,
                "emails": []
            }

    except Exception as e:
        return {"error": str(e)}

@app.post("/extract-batch")
async def extract_emails_batch(request: BatchURLRequest):
    results = []
    for url in request.urls:
        try:
            result = await scrape_website(url, max_count=2)

            if isinstance(result, set):
                emails = list(result)
                results.append({
                    "url": url,
                    "email": emails[0] if emails else None,
                    "all_emails": emails
                })
            elif isinstance(result, str):
                results.append({
                    "url": url,
                    "email": result,
                    "all_emails": []
                })
            else:
                results.append({
                    "url": url,
                    "email": None,
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
