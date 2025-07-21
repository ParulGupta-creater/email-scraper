from fastapi import FastAPI
from pydantic import BaseModel
from playwright_scraper import scrape_with_playwright
import traceback

app = FastAPI()

class URLRequest(BaseModel):
    url: str

@app.get("/")
def root():
    return {"message": "Playwright Email Scraper is live"}

@app.post("/extract-playwright")
async def extract_emails_playwright(request: URLRequest):
    try:
        result = await scrape_with_playwright(request.url)
        if isinstance(result, set):
            emails = list(result)
            return {"email": emails[0] if emails else None, "emails": emails}
        return {"email": result, "emails": []}
    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "email": None,
            "emails": []
        }
