"""
Broad search-engine-based scraper: catches Indeed.de, StepStone, Kimeta,
praktischArzt, and hospital career pages not individually coded, by running
targeted German queries through DuckDuckGo's HTML search endpoint.
"""
import time
from urllib.parse import unquote, urlparse, parse_qs
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from filters import is_relevant, extract_specialty, extract_level, is_berlin_area, SKIP_DOMAINS

QUERIES = [
    # Berlin-focused
    "Assistenzarzt Chirurgie Berlin Stellenangebot",
    "Assistenzarzt Unfallchirurgie Berlin Stellenangebot",
    "Assistenzarzt Orthopädie Unfallchirurgie Berlin",
    "Arzt in Weiterbildung Chirurgie Berlin",
    "Facharzt Unfallchirurgie Berlin Stellenangebot",
    "Common Trunk Chirurgie Berlin",
    # Brandenburg / nearby
    "Assistenzarzt Chirurgie Brandenburg Stellenangebot",
    "Assistenzarzt Unfallchirurgie Potsdam",
    "Assistenzarzt Chirurgie Potsdam Stellenangebot",
    # Wider net, Germany-wide (still useful, sorted below Berlin results)
    "Assistenzarzt Unfallchirurgie Stellenangebot Deutschland",
    "Assistenzarzt Chirurgie Weiterbildung Stellenangebot",
]

DDG_URL = "https://html.duckduckgo.com/html/"
MIN_TITLE_LEN = 8


def _extract_real_url(href):
    if not href:
        return ""
    if "uddg=" in href:
        qs = parse_qs(urlparse(href).query)
        uddg = qs.get("uddg", [""])[0]
        return unquote(uddg) if uddg else ""
    return href if href.startswith("http") else ""


class SearchScraper(BaseScraper):
    name = "search"

    def scrape(self) -> list:
        results = []
        seen = set()

        for query in QUERIES:
            try:
                r = self.fetch(DDG_URL, params={"q": query, "kl": "de-de"})
                soup = BeautifulSoup(r.text, "lxml")
                for result in soup.select(".result"):
                    a = result.select_one(".result__a")
                    snippet_el = result.select_one(".result__snippet")
                    if not a:
                        continue

                    title = a.get_text(strip=True)
                    url = _extract_real_url(a.get("href", ""))
                    if not url or url in seen or any(d in url for d in SKIP_DOMAINS):
                        continue
                    if len(title) < MIN_TITLE_LEN:
                        continue

                    desc = snippet_el.get_text(strip=True) if snippet_el else ""
                    combined = f"{title} {desc}"

                    if not is_relevant(combined):
                        continue

                    seen.add(url)
                    results.append({
                        "title": title,
                        "source": "search",
                        "url": url,
                        "employer": None,
                        "location": "Berlin" if is_berlin_area(combined) else None,
                        "berlin_area": is_berlin_area(combined),
                        "specialty": extract_specialty(combined),
                        "level": extract_level(combined),
                        "description": desc,
                    })
                time.sleep(2)
            except Exception as e:
                print(f"[Search] error on '{query}': {e}")

        return results
