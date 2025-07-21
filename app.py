from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from playwright_scraper import scrape_with_playwright

app = FastAPI()

class URLRequest(BaseModel):
    url: str

@app.get("/")
def root():
    return {"message": "Email Scraper API is running"}

@app.post("/extract-playwright")
async def extract_emails_playwright(request: URLRequest):
    try:
        result = await scrape_with_playwright(request.url)

        if isinstance(result, set):
            emails = list(result)
            return {
                "email": emails[0] if emails else None,
                "emails": emails
            }
        else:
            return {"email": result, "emails": []}

    except Exception as e:
        return {
            "email": "Error",
            "emails": [],
            "error": str(e)
        }
