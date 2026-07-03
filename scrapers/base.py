import requests
from abc import ABC, abstractmethod

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


class BaseScraper(ABC):
    name = "base"

    def fetch(self, url, params=None, timeout=15):
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r

    @abstractmethod
    def scrape(self) -> list:
        """Return list of opportunity dicts."""
        ...
