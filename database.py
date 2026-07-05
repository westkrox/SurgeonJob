import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Renamed from opportunities.db: that file was switched into WAL mode by a
# previous version of this code, and WAL mode is stored in the database file
# itself (not just per-connection), so it kept hanging on Render's disk even
# after the PRAGMA was removed here. Nothing of value had been saved into it
# yet, so starting fresh under a new filename sidesteps the poisoned file
# instead of trying to repair it without shell access.
DB_PATH = Path(__file__).parent / "opportunities_v2.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL mode was tried here to avoid "database is locked" errors, but its
    # shared-memory-mapped -wal/-shm files hang indefinitely on Render's disk.
    # With a single gunicorn worker, busy_timeout alone is enough to
    # serialize the threads' connections safely.
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            employer TEXT,
            location TEXT,
            berlin_area INTEGER DEFAULT 0,
            specialty TEXT DEFAULT '[]',
            level TEXT DEFAULT '[]',
            description TEXT,
            scraped_at TEXT NOT NULL,
            status TEXT DEFAULT 'new'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            finished_at TEXT,
            total_found INTEGER DEFAULT 0,
            total_new INTEGER DEFAULT 0,
            error TEXT
        )
    """)
    conn.commit()
    conn.close()


def upsert_opportunity(opp):
    conn = get_connection()
    try:
        cur = conn.execute("""
            INSERT INTO opportunities
                (title, source, url, employer, location, berlin_area, specialty, level, description, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                employer = excluded.employer,
                location = excluded.location,
                berlin_area = excluded.berlin_area,
                specialty = excluded.specialty,
                level = excluded.level,
                description = excluded.description,
                scraped_at = excluded.scraped_at
        """, (
            opp["title"], opp["source"], opp["url"],
            opp.get("employer"), opp.get("location"),
            1 if opp.get("berlin_area") else 0,
            json.dumps(opp.get("specialty", [])),
            json.dumps(opp.get("level", [])),
            opp.get("description"),
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_opportunities(status=None, source=None, berlin_only=False,
                      specialty=None, level=None, search=None,
                      sort="newest", scraped_within_days=None):
    conn = get_connection()
    query = "SELECT * FROM opportunities WHERE 1=1"
    params = []
    if status and status != "all":
        query += " AND status = ?"
        params.append(status)
    if source and source != "all":
        query += " AND source = ?"
        params.append(source)
    if berlin_only:
        query += " AND berlin_area = 1"
    if specialty:
        query += " AND (" + " OR ".join(["specialty LIKE ?"] * len(specialty)) + ")"
        params.extend(f"%{s}%" for s in specialty)
    if level:
        query += " AND (" + " OR ".join(["level LIKE ?"] * len(level)) + ")"
        params.extend(f"%{lv}%" for lv in level)
    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR employer LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if scraped_within_days:
        query += " AND scraped_at >= datetime('now', ?)"
        params.append(f"-{scraped_within_days} days")

    if sort == "berlin_first":
        query += """
            ORDER BY
              CASE status WHEN 'new' THEN 0 WHEN 'interested' THEN 1 WHEN 'applied' THEN 2 ELSE 3 END,
              berlin_area DESC,
              scraped_at DESC
        """
    else:
        query += """
            ORDER BY
              CASE status WHEN 'new' THEN 0 WHEN 'interested' THEN 1 WHEN 'applied' THEN 2 ELSE 3 END,
              scraped_at DESC
        """

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_status(opp_id, status):
    conn = get_connection()
    conn.execute("UPDATE opportunities SET status = ? WHERE id = ?", (status, opp_id))
    conn.commit()
    conn.close()


def delete_opportunity(opp_id):
    conn = get_connection()
    conn.execute("DELETE FROM opportunities WHERE id = ?", (opp_id,))
    conn.commit()
    conn.close()


def get_sources():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT source FROM opportunities ORDER BY source").fetchall()
    conn.close()
    return [r["source"] for r in rows]


def log_scrape_start():
    conn = get_connection()
    cur = conn.execute("INSERT INTO scrape_log (started_at) VALUES (?)", (datetime.utcnow().isoformat(),))
    conn.commit()
    log_id = cur.lastrowid
    conn.close()
    return log_id


def log_scrape_finish(log_id, total_found, total_new, error=None):
    conn = get_connection()
    conn.execute(
        "UPDATE scrape_log SET finished_at=?, total_found=?, total_new=?, error=? WHERE id=?",
        (datetime.utcnow().isoformat(), total_found, total_new, error, log_id)
    )
    conn.commit()
    conn.close()


def get_last_scrape():
    conn = get_connection()
    row = conn.execute("SELECT * FROM scrape_log ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None
