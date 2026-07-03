# Surgery Jobs — Berlin

Scrapes German surgical residency openings (Assistenzarzt/Facharzt Chirurgie,
Unfallchirurgie, and related specialties), with a bias toward Berlin/Brandenburg,
into a mobile-friendly dashboard you can triage from your phone.

Sources: Ärztestellen (Deutsches Ärzteblatt job board), direct scraping of
Vivantes / Charité / BG Klinikum Unfallkrankenhaus Berlin career pages, and a
broad DuckDuckGo-search pass covering Indeed.de, StepStone, Kimeta, and other
hospital sites.

## Run locally

```
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Deploy for free so it works from your iPhone anywhere

1. **Push this folder to a new GitHub repo** (private is fine).
2. **Render.com** → New → Web Service → connect the repo. It will detect
   `render.yaml` automatically (free plan, Python, gunicorn).
3. In the Render dashboard, set two environment variables:
   - `APP_PASSWORD` — a password of your choosing; the whole site will
     require this via a login prompt (recommended since it'll be public).
   - `SCRAPE_TOKEN` — a second secret used only by the automated scraper
     trigger below (can be the same value as `APP_PASSWORD` if you want one
     less thing to remember).
4. Deploy. Render gives you a URL like `https://surgeon-job-scraper.onrender.com`.
5. **Keep it scraping even when you're not looking at it**: free Render web
   services sleep after ~15 min idle, so an internal timer alone won't fire
   reliably. This repo includes a GitHub Actions workflow
   (`.github/workflows/scrape.yml`) that pings `/api/scrape` three times a
   day and also wakes the app. In your GitHub repo → Settings → Secrets and
   variables → Actions, add:
   - `RENDER_APP_URL` — your Render URL (no trailing slash)
   - `SCRAPE_TOKEN` — same value you set on Render
6. **Add to your iPhone home screen**: open the Render URL in Safari → Share
   → "Add to Home Screen". It'll open full-screen like a native app.

### Known limitations of the free tier

- Render's free plan spins the app down after idle periods; the first load
  after a while asleep takes ~30-60 seconds to wake up.
- Free-tier disk isn't guaranteed to persist across redeploys (it does
  persist across normal sleep/wake). If you push a code change and the job
  list looks empty afterward, just tap **Scrape** again.
- Site-specific scrapers (Vivantes/Charité/UKB) key off URL patterns that
  can change if those sites redesign; the DuckDuckGo-search scraper is the
  fallback net and doesn't depend on any single site's markup.

## Notes

- All matching is keyword-based on German medical terminology
  (`Assistenzarzt`, `Unfallchirurgie`, etc.) — see `filters.py` to tune it.
- Mark jobs **Interested** / **Applied** / **Dismiss** from the dashboard;
  status persists in the database.
