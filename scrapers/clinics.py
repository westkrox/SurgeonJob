"""
Direct scraping of career pages for specific Berlin-area hospitals that are
strong targets for surgical/trauma residencies: Vivantes (largest non-university
hospital group in Berlin), Charite (university hospital), and the BG Klinikum
Unfallkrankenhaus Berlin (the dedicated trauma hospital).
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper
from filters import is_relevant, extract_specialty, extract_level, is_berlin_area

# Each site: base url, listing page(s) to fetch, and href substrings that
# identify an individual job posting link (vs nav/category links).
SITES = [
    {
        "name": "vivantes",
        "base": "https://karriere.vivantes.de",
        "listing_paths": ["/jobs/"],
        "job_href_markers": ["/stellenangebote/detail/", "/unsere-berufe/"],
        "hint": "berlin",
    },
    {
        "name": "charite",
        "base": "https://karriere.charite.de",
        "listing_paths": ["/stellenangebote", "/en/job-vacancies"],
        "job_href_markers": ["/stellenangebote/detail/", "/job-vacancies/detail/"],
        "hint": "berlin",
    },
    {
        "name": "ukb_bgklinik",
        "base": "https://www.bg-kliniken.de",
        "listing_paths": ["/unfallkrankenhaus-berlin/karriere/offene-stellen/"],
        "job_href_markers": ["/karriere/offene-stellen/"],
        "exclude_exact_paths": ["/unfallkrankenhaus-berlin/karriere/offene-stellen/"],
        "hint": "unfallchirurgie unfallkrankenhaus berlin trauma",
    },
]

MIN_TITLE_LEN = 8


class ClinicsScraper(BaseScraper):
    name = "clinics"

    def scrape(self) -> list:
        results = []
        seen = set()

        for site in SITES:
            excluded = set(site.get("exclude_exact_paths", []))
            for path in site["listing_paths"]:
                url = urljoin(site["base"], path)
                try:
                    r = self.fetch(url)
                except Exception as e:
                    print(f"[Clinics/{site['name']}] error fetching {path}: {e}")
                    continue

                soup = BeautifulSoup(r.text, "lxml")
                all_links = soup.select("a[href]")
                matched = [a for a in all_links if any(m in a.get("href", "") for m in site["job_href_markers"])]
                print(f"[Clinics/{site['name']}] {path} -> HTTP {r.status_code}, {len(r.text)} bytes, "
                      f"{len(all_links)} total links, {len(matched)} matching job-href pattern")
                kept = 0

                for a in soup.select("a[href]"):
                    href = a.get("href", "")
                    if not href:
                        continue
                    if not any(marker in href for marker in site["job_href_markers"]):
                        continue
                    if href.rstrip("/") in {p.rstrip("/") for p in excluded}:
                        continue

                    job_url = urljoin(site["base"], href)
                    if job_url in seen:
                        continue

                    title = a.get_text(strip=True)
                    if len(title) < MIN_TITLE_LEN:
                        continue

                    container = a.find_parent(["li", "article", "div"]) or a.parent
                    snippet = container.get_text(" ", strip=True) if container else ""
                    snippet = snippet[:400]

                    combined = f"{title} {snippet} {site['hint']}"
                    if not is_relevant(combined):
                        continue

                    seen.add(job_url)
                    results.append({
                        "title": title,
                        "source": site["name"],
                        "url": job_url,
                        "employer": None,
                        "location": "Berlin" if is_berlin_area(combined) else None,
                        "berlin_area": is_berlin_area(combined),
                        "specialty": extract_specialty(combined),
                        "level": extract_level(combined),
                        "description": snippet,
                    })
                    kept += 1

                print(f"[Clinics/{site['name']}] {path} -> kept {kept} after relevance filter")

        return results
