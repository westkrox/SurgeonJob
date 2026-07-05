"""
BG Klinikum Unfallkrankenhaus Berlin (UKB) job postings.

UKB's career page doesn't have job listings in its static HTML - they're
loaded client-side by a "b-ite.com" jobs widget. Instead of driving a
headless browser, this calls the same JSON API the widget itself calls
(found by inspecting its network requests): https://jobs.b-ite.com/api/v1/postings/search

The "key" below is not a secret - it's a plain string embedded in UKB's own
public JS bundle (cs-assets.b-ite.com/klinikverbund-gesetzlichen-unfallversicherung-kuv/
jobs-api/main-listing.min.js), the same one any visitor's browser downloads
to render the "open positions" widget. This request is functionally
identical to what that widget does.
"""
import re
import requests
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, HEADERS
from filters import is_relevant, extract_specialty, extract_level

API_URL = "https://jobs.b-ite.com/api/v1/postings/search"
CUSTOMER_KEY = "88752983b2312a3429bf876d701d76713201ff73"
PAGE_URL = "https://www.bg-kliniken.de/unfallkrankenhaus-berlin/karriere/offene-stellen/"


def _strip_html(html):
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text(" ", strip=True)


class BGKlinikenScraper(BaseScraper):
    name = "ukb_bgklinik"

    def scrape(self) -> list:
        payload = {
            "key": CUSTOMER_KEY,
            "channel": 0,
            "locale": "de",
            "sort": {"by": "startsOn", "order": "desc"},
            "origin": PAGE_URL,
            "page": {"num": 1000, "offset": 0},
            "filter": {"custom.einsatzort": {"in": ["berlin"]}},
        }
        try:
            r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[BGKliniken] error fetching postings: {e}")
            return []

        postings = data.get("jobPostings", [])
        print(f"[BGKliniken] {len(postings)} total postings returned")

        results = []
        for p in postings:
            title = p.get("title", "")
            custom = p.get("custom", {})
            # einleitungstext is generic employer boilerplate that mentions
            # "BG Klinikum" on nearly every posting regardless of specialty,
            # which falsely matches the "bg klinik" trauma keyword. Only
            # aufgaben/profil are actually job-specific, so classification
            # uses those; einleitungstext is still shown in the description.
            job_specific = " ".join(_strip_html(custom.get(field, "")) for field in
                                     ("aufgaben", "profil"))
            combined = f"{title} {job_specific}"

            if not is_relevant(combined):
                continue

            intro = _strip_html(custom.get("einleitungstext", ""))
            snippet = f"{intro} {job_specific}"

            employer = (p.get("employer") or {}).get("name")
            city = (p.get("address") or {}).get("city")
            location = city or "Berlin"

            results.append({
                "title": title,
                "source": "ukb_bgklinik",
                "url": p.get("url") or PAGE_URL,
                "employer": employer,
                "location": location,
                "berlin_area": True,  # API request already filters custom.einsatzort=berlin
                "specialty": extract_specialty(combined),
                "level": extract_level(combined),
                "description": re.sub(r"\s+", " ", snippet)[:400],
            })

        print(f"[BGKliniken] kept {len(results)} after relevance filter")
        return results
