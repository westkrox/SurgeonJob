"""
Scraper for aerztestellen.aerzteblatt.de — the Deutsches Aerzteblatt physician
job board. Structured, reliable source for German hospital residency postings.
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from filters import is_relevant, extract_specialty, extract_level, is_berlin_area

BASE = "https://aerztestellen.aerzteblatt.de"

# (path, hint) — hint is extra German context text merged in for keyword
# extraction/filtering, since the URL already implies specialty/level that
# may not appear verbatim in a truncated listing snippet.
CATEGORY_PATHS = [
    ("/de/stellen/assistenzarzt-arzt-weiterbildung/chirurgie-uebersicht",
     "assistenzarzt chirurgie"),
    ("/de/stellen/assistenzarzt-arzt-weiterbildung/chirurgie-0/berlin",
     "assistenzarzt chirurgie berlin"),
    ("/de/stellen/assistenzarzt-arzt-weiterbildung/orthopadie-und-unfallchirurgie",
     "assistenzarzt orthopädie und unfallchirurgie"),
    ("/de/stellen/assistenzarzt-arzt-weiterbildung/orthopadie-und-unfallchirurgie/berlin",
     "assistenzarzt orthopädie und unfallchirurgie berlin"),
    ("/de/stellen/orthopadie-und-unfallchirurgie/berlin",
     "orthopädie und unfallchirurgie berlin"),
    ("/de/stellen/orthopadie-und-unfallchirurgie",
     "orthopädie und unfallchirurgie"),
    ("/de/stellen/chirurgie-uebersicht",
     "chirurgie"),
]

MIN_TITLE_LEN = 8


class AerztestellenScraper(BaseScraper):
    name = "aerztestellen"

    def scrape(self) -> list:
        results = []
        seen = set()

        for path, hint in CATEGORY_PATHS:
            try:
                r = self.fetch(urljoin(BASE, path))
            except Exception as e:
                print(f"[Aerztestellen] error fetching {path}: {e}")
                continue

            soup = BeautifulSoup(r.text, "lxml")
            links = soup.select('a[href*="/de/stelle/"]')
            print(f"[Aerztestellen] {path} -> HTTP {r.status_code}, {len(r.text)} bytes, {len(links)} job links found")
            kept = 0

            for a in links:
                href = a.get("href", "")
                if not href or "/de/stelle/" not in href:
                    continue
                url = urljoin(BASE, href)
                if url in seen:
                    continue

                title = a.get_text(strip=True)
                if len(title) < MIN_TITLE_LEN:
                    continue

                # Pull surrounding context (employer/location line usually
                # sits in the same card as the title link).
                container = a.find_parent(["li", "article", "div"]) or a.parent
                snippet = container.get_text(" ", strip=True) if container else ""
                snippet = snippet[:400]

                combined = f"{title} {snippet} {hint}"
                if not is_relevant(combined):
                    continue

                seen.add(url)
                results.append({
                    "title": title,
                    "source": "aerztestellen",
                    "url": url,
                    "employer": None,
                    "location": "Berlin" if is_berlin_area(combined) else None,
                    "berlin_area": is_berlin_area(combined),
                    "specialty": extract_specialty(combined),
                    "level": extract_level(combined),
                    "description": snippet,
                })
                kept += 1

            print(f"[Aerztestellen] {path} -> kept {kept} after relevance filter")

        return results
