from fastapi import FastAPI
from pydantic import BaseModel
from email_scraper import extract_emails_from_url

app = FastAPI()

class URLRequest(BaseModel):
    url: str

@app.get("/")
def root():
    return {"message": "Email Scraper API is running"}

@app.post("/extract")
def extract_emails(request: URLRequest):
    try:
        emails, source = extract_emails_from_url(request.url)
        return {
            "email": emails[0] if emails else None,
            "emails": emails,
            "source": source
        }
    except Exception as e:
        return {"error": str(e)}
