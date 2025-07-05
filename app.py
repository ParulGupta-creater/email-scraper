from fastapi import FastAPI
from pydantic import BaseModel
from email_scraper import scrape_website

app = FastAPI()

class URLRequest(BaseModel):
    url: str

@app.get("/")
def root():
    return {"message": "Email Scraper API is running"}

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
