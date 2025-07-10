from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import asyncio
from email_scraper import scrape_website

app = FastAPI()

# Request models
class URLRequest(BaseModel):
    url: str

class BatchURLRequest(BaseModel):
    urls: List[str]

@app.get("/")
def root():
    return {"message": "Email Scraper API is running."}

@app.post("/extract")
async def extract_emails(request: URLRequest):
    result = await scrape_website(request.url, max_count=5)
    return result

@app.post("/extract-batch")
async def extract_emails_batch(request: BatchURLRequest):
    async def process_url(url: str):
        try:
            result = await scrape_website(url, max_count=5)
            result["url"] = url
            return result
        except Exception as e:
            return {
                "url": url,
                "status": "error",
                "email": None,
                "emails": [],
                "error": str(e)
            }

    tasks = [process_url(url) for url in request.urls]
    results = await asyncio.gather(*tasks)
    return results
