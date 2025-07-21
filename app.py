from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
import traceback

from playwright_scraper import scrape_with_playwright


app = FastAPI()

class URLRequest(BaseModel):
    url: str

class BatchURLRequest(BaseModel):
    urls: List[str]

@app.get("/")
def root():
    return {"message": "Email Scraper API is running"}

@app.post("/extract-bs")
async def extract_emails_bs(request: URLRequest):
    try:
        result = scrape_bs(request.url)
        if isinstance(result, set):
            emails = list(result)
            return {
                "email": emails[0] if emails else None,
                "emails": emails,
                "status": "✅ Email"
            }
        else:
            return {
                "email": result,
                "emails": [],
                "status": "❌ " + result
            }
    except Exception as e:
        return {
            "email": "Error",
            "emails": [],
            "status": "❌ Exception in BeautifulSoup",
            "error": str(e)
        }

@app.post("/extract-playwright")
async def extract_emails_playwright(request: URLRequest):
    try:
        result = await scrape_with_playwright(request.url)
        if isinstance(result, set):
            emails = list(result)
            return {
                "email": emails[0] if emails else None,
                "emails": emails,
                "status": "✅ Email"
            }
        else:
            return {
                "email": result,
                "emails": [],
                "status": "❌ " + result
            }
    except Exception as e:
        return {
            "email": "Error",
            "emails": [],
            "status": "❌ Exception in Playwright",
            "error": str(e)
        }
