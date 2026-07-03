import os
import json
import threading
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response
from flask_apscheduler import APScheduler
import database as db
from scrapers import ALL_SCRAPERS

app = Flask(__name__)
scheduler = APScheduler()

APP_PASSWORD = os.environ.get("APP_PASSWORD")
SCRAPE_TOKEN = os.environ.get("SCRAPE_TOKEN", APP_PASSWORD)

_scrape_status = {"running": False, "progress": "", "last_run": None}


def _check_auth(username, password):
    return password == APP_PASSWORD


def require_auth(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not APP_PASSWORD:
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not _check_auth(auth.username, auth.password):
            return Response(
                "Login required", 401,
                {"WWW-Authenticate": 'Basic realm="Surgeon Jobs"'}
            )
        return f(*args, **kwargs)
    return wrapped


@app.before_request
def _global_auth():
    # Let the cron-triggered scrape endpoint authenticate via token instead
    # of basic auth, so an external scheduler can call it headlessly.
    if request.path == "/api/scrape" and request.method == "POST":
        token = request.args.get("token") or request.headers.get("X-Scrape-Token")
        if SCRAPE_TOKEN and token == SCRAPE_TOKEN:
            return None
    if not APP_PASSWORD:
        return None
    auth = request.authorization
    if not auth or not _check_auth(auth.username, auth.password):
        return Response(
            "Login required", 401,
            {"WWW-Authenticate": 'Basic realm="Surgeon Jobs"'}
        )
    return None


def run_all_scrapers():
    if _scrape_status["running"]:
        return {"error": "Scrape already in progress"}

    _scrape_status["running"] = True
    _scrape_status["progress"] = "Starting..."
    total_found = 0
    total_new = 0
    log_id = None

    try:
        log_id = db.log_scrape_start()
        for ScraperClass in ALL_SCRAPERS:
            scraper = ScraperClass()
            _scrape_status["progress"] = f"Scraping {scraper.name}..."
            print(f"[Scraper] Running {scraper.name}")
            try:
                items = scraper.scrape()
                print(f"[Scraper] {scraper.name} found {len(items)} items")
                for opp in items:
                    total_found += 1
                    row_id = db.upsert_opportunity(opp)
                    if row_id:
                        total_new += 1
            except Exception as e:
                print(f"[Scraper] {scraper.name} failed: {e}")

        db.log_scrape_finish(log_id, total_found, total_new)
        _scrape_status["last_run"] = datetime.utcnow().isoformat()
        _scrape_status["progress"] = f"Done. Found {total_found} total, {total_new} new."
        print(f"[Scraper] Finished. {total_found} found, {total_new} new.")
    except Exception as e:
        print(f"[Scraper] run_all_scrapers crashed: {e}")
        if log_id is not None:
            db.log_scrape_finish(log_id, total_found, total_new, error=str(e))
        _scrape_status["progress"] = f"Error: {e}"
    finally:
        _scrape_status["running"] = False

    return {"found": total_found, "new": total_new}


# --- Routes ---

@app.route("/")
def index():
    sources = db.get_sources()
    last_scrape = db.get_last_scrape()
    return render_template("index.html", sources=sources, last_scrape=last_scrape)


@app.route("/api/opportunities")
def api_opportunities():
    status = request.args.get("status", "all")
    source = request.args.get("source", "all")
    berlin_only = request.args.get("berlin_only") == "1"
    specialty = [s for s in request.args.getlist("specialty") if s]
    level = [lv for lv in request.args.getlist("level") if lv]
    search = request.args.get("search", "").strip() or None
    sort = request.args.get("sort", "newest")
    fresh_days = request.args.get("fresh_days")
    fresh_days = int(fresh_days) if fresh_days and fresh_days.isdigit() else None

    opps = db.get_opportunities(
        status=status, source=source, berlin_only=berlin_only,
        specialty=specialty, level=level, search=search,
        sort=sort, scraped_within_days=fresh_days
    )

    for opp in opps:
        try:
            opp["specialty"] = json.loads(opp.get("specialty") or "[]")
        except Exception:
            opp["specialty"] = []
        try:
            opp["level"] = json.loads(opp.get("level") or "[]")
        except Exception:
            opp["level"] = []

    return jsonify(opps)


@app.route("/api/opportunities/<int:opp_id>/status", methods=["POST"])
def api_update_status(opp_id):
    data = request.get_json()
    status = data.get("status")
    if status not in ("new", "interested", "applied", "dismissed"):
        return jsonify({"error": "invalid status"}), 400
    db.update_status(opp_id, status)
    return jsonify({"ok": True})


@app.route("/api/opportunities/<int:opp_id>", methods=["DELETE"])
def api_delete(opp_id):
    db.delete_opportunity(opp_id)
    return jsonify({"ok": True})


@app.route("/api/opportunities", methods=["POST"])
def api_add():
    data = request.get_json()
    if not data.get("title") or not data.get("url"):
        return jsonify({"error": "title and url are required"}), 400
    from filters import extract_specialty, extract_level, is_berlin_area
    combined = f"{data['title']} {data.get('description', '')}"
    opp = {
        "title": data["title"],
        "source": "manual",
        "url": data["url"],
        "employer": data.get("employer"),
        "location": data.get("location"),
        "berlin_area": is_berlin_area(combined),
        "specialty": extract_specialty(combined),
        "level": extract_level(combined),
        "description": data.get("description", ""),
    }
    db.upsert_opportunity(opp)
    return jsonify({"ok": True})


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    if _scrape_status["running"]:
        return jsonify({"error": "Already running"}), 409
    thread = threading.Thread(target=run_all_scrapers, daemon=True)
    thread.start()
    return jsonify({"ok": True, "message": "Scrape started"})


@app.route("/api/scrape/status")
def api_scrape_status():
    return jsonify(_scrape_status)


@app.route("/api/sources")
def api_sources():
    return jsonify(db.get_sources())


# --- Scheduler (best-effort; the external GitHub Actions cron is the
# reliable trigger for a free host that sleeps when idle) ---

SCRAPE_HOUR = 7
SCRAPE_MINUTE = 0


class Config:
    SCHEDULER_API_ENABLED = False
    JOBS = [
        {
            "id": "daily_scrape",
            "func": "app:run_all_scrapers",
            "trigger": "cron",
            "hour": SCRAPE_HOUR,
            "minute": SCRAPE_MINUTE,
        }
    ]


app.config.from_object(Config)
scheduler.init_app(app)

db.init_db()
scheduler.start()

if db.get_last_scrape() is None:
    print("No previous scrape found — starting initial scrape in background...")
    threading.Thread(target=run_all_scrapers, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Surgeon Jobs Dashboard running at http://127.0.0.1:{port}")
    app.run(debug=False, host="0.0.0.0", port=port)
