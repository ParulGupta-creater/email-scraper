from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
from email_scraper import scrape_website   # <-- now exists in email_scraper.py

app = FastAPI(title="Email Scraper API")

# ---------- Request models ----------
class URLRequest(BaseModel):
    url: str

class BatchURLRequest(BaseModel):
    urls: List[str]

# ---------- Health check ----------
@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Email Scraper API is running"}

# ---------- Single‑URL endpoint ----------
@app.post("/extract")
def extract_emails(request: URLRequest) -> Union[dict, str]:
    try:
        result = scrape_website(request.url, max_count=5)

        # If the scraper returns a set → valid emails found
        if isinstance(result, set):
            emails = list(result)
            return {
                "email": emails[0] if emails else None,
                "emails": emails
            }

        # Otherwise the scraper returns a string: "Contact Form" or "No Email"
        return {
            "email": result,
            "emails": []
        }

    except Exception as exc:
        return {"error": str(exc)}

# ---------- Batch endpoint ----------
@app.post("/extract-batch")
def extract_emails_batch(request: BatchURLRequest) -> List[dict]:
    results: List[dict] = []

    for url in request.urls:
        try:
            result = scrape_website(url, max_count=5)

            if isinstance(result, set):
                emails = list(result)
                results.append(
                    {
                        "url": url,
                        "email": emails[0] if emails else None,
                        "all_emails": emails,
                    }
                )
            else:
                results.append(
                    {
                        "url": url,
                        "email": result,        # "Contact Form" | "No Email"
                        "all_emails": [],
                    }
                )

        except Exception as exc:
            results.append(
                {
                    "url": url,
                    "error": str(exc),
                    "email": None,
                    "all_emails": [],
                }
            )

    return results
