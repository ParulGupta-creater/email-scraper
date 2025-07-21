from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
from fastapi.responses import JSONResponse

from playwright_scraper import scrape_with_playwright
from beautifulsoup_scraper import scrape_bs

app = FastAPI()

class URLRequest(BaseModel):
    url: str

class BatchURLRequest(BaseModel):
    urls: List[str]

@app.get("/")
def root():
    return {"message": "✅ Email Scraper API is running"}

@app.post("/extract-bs")
async def extract_emails_bs(request: URLRequest):
    try:
        result = scrape_bs(request.url)
        if isinstance(result, set):
            emails = list(result)
            return {
                "email": emails[0] if emails else None,
                "emails": emails,
                "error": None
            }
        else:
            return {
                "email": result,
                "emails": [],
                "error": None
            }
    except Exception as e:
        return JSONResponse(
            content={
                "email": "No Email",
                "emails": [],
                "error": str(e)
            },
            status_code=500
        )

@app.post("/extract-playwright")
async def extract_emails_playwright(request: URLRequest):
    try:
        result = await scrape_with_playwright(request.url)
        if isinstance(result, set):
            emails = list(result)
            return {
                "email": emails[0] if emails else None,
                "emails": emails,
                "error": None
            }
        else:
            return {
                "email": result,
                "emails": [],
                "error": None
            }
    except Exception as e:
        return JSONResponse(
            content={
                "email": "No Email",
                "emails": [],
                "error": str(e)
            },
            status_code=500
        )
