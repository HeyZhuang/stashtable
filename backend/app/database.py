import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import DB_PATH, DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS satellites (
    norad_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    intl_designator TEXT,
    object_type TEXT,
    owner TEXT,
    launch_date TEXT,
    period REAL,
    inclination REAL,
    apogee REAL,
    perigee REAL,
    tle_line1 TEXT,
    tle_line2 TEXT,
    source_group TEXT DEFAULT 'active',
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_satellites_name ON satellites(name);
CREATE INDEX IF NOT EXISTS idx_satellites_group ON satellites(source_group);
CREATE INDEX IF NOT EXISTS idx_satellites_orbit ON satellites(apogee, perigee);

CREATE TABLE IF NOT EXISTS iss_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    norad_id INTEGER NOT NULL DEFAULT 25544,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    altitude REAL NOT NULL,
    velocity REAL NOT NULL,
    visibility TEXT,
    observed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (norad_id) REFERENCES satellites(norad_id)
);
CREATE INDEX IF NOT EXISTS idx_iss_observed ON iss_positions(observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_iss_norad_time ON iss_positions(norad_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS space_weather (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time_tag TEXT NOT NULL UNIQUE,
    kp REAL NOT NULL,
    level TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_weather_time ON space_weather(time_tag DESC);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    satellite_id INTEGER NOT NULL,
    observer_name TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (satellite_id) REFERENCES satellites(norad_id)
);
CREATE INDEX IF NOT EXISTS idx_observations_sat ON observations(satellite_id);

CREATE TABLE IF NOT EXISTS collection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    record_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_collection_created ON collection_logs(created_at DESC);
"""

def utcnow():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db():
    with db() as con:
        con.executescript(SCHEMA)
        # 初始演示账号所观测的目标必须存在，外键才能成立
        con.execute("""INSERT OR IGNORE INTO satellites
            (norad_id,name,intl_designator,object_type,owner,launch_date,source_group,updated_at)
            VALUES (25544,'ISS (ZARYA)','1998-067A','PAY','US/Russia','1998-11-20','stations',?)""", (utcnow(),))

def log_collection(source, status, detail="", count=0):
    with db() as con:
        con.execute("INSERT INTO collection_logs(source,status,detail,record_count,created_at) VALUES(?,?,?,?,?)",
                    (source, status, str(detail)[:500], count, utcnow()))
