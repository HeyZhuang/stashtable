import asyncio
import csv
import io
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from ..config import DATA_DIR, CACHE_TTL
from ..database import db, log_collection, utcnow

CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php"
ISS_URL = "https://api.wheretheiss.at/v1/satellites/25544"
KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
GROUP_FILES = {
    "active": "active.tle", "stations": "stations.tle", "visual": "visual.tle",
    "gps-ops": "gps-ops.tle", "beidou": "beidou.tle", "starlink": "starlink.tle",
}

# Redis 缓存（可选，有则用 Redis，无则回退内存）
try:
    import redis
    _redis = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0, decode_responses=True, socket_timeout=2
    )
    _redis.ping()
    REDIS_AVAILABLE = True
except Exception:
    _redis = None
    REDIS_AVAILABLE = False

_cache = {}

def cache_get(key):
    """统一缓存读取"""
    if REDIS_AVAILABLE:
        try:
            data = _redis.get(f"satdash:{key}")
            if data:
                return json.loads(data)
        except Exception:
            pass
    item = _cache.get(key)
    if item and time.time() - item["time"] < CACHE_TTL.get(key.split(":")[0], 60):
        return item["value"]
    return None

def cache_set(key, value, ttl=None):
    """统一缓存写入"""
    if REDIS_AVAILABLE:
        try:
            _redis.setex(f"satdash:{key}", ttl or 300, json.dumps(value))
        except Exception:
            pass
    _cache[key] = {"time": time.time(), "value": value}

class ExternalServiceError(RuntimeError):
    pass

def cached(key, ttl, producer):
    # 先尝试从缓存读
    cached_val = cache_get(key)
    if cached_val is not None:
        return cached_val
    try:
        value = producer()
        cache_set(key, value, ttl)
        return value
    except Exception as exc:
        # 失败时尝试读旧缓存
        item = _cache.get(key)
        if item:
            stale = dict(item["value"]) if isinstance(item["value"], dict) else {"data": item["value"]}
            stale.update({"degraded": True, "stale": True, "message": "外部接口暂不可用，当前显示最近成功缓存"})
            return stale
        raise ExternalServiceError(str(exc)) from exc

def read_tle_text(group="active"):
    filename = GROUP_FILES.get(group, "active.tle")
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(filename)
    text = path.read_text(encoding="utf-8", errors="replace").replace("\r", "")
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    records = []
    for i in range(0, len(lines) - 2, 3):
        if lines[i+1].startswith("1 ") and lines[i+2].startswith("2 "):
            records.append({"name": lines[i], "line1": lines[i+1], "line2": lines[i+2],
                            "norad_id": int(lines[i+1][2:7])})
    return records

def load_catalog():
    path = DATA_DIR / "satcat.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", errors="replace") as f:
        rows = csv.DictReader(f)
        return {int(r["NORAD_CAT_ID"]): r for r in rows if (r.get("NORAD_CAT_ID") or "").isdigit()}

def refresh_tle(group="active"):
    """在线刷新失败时，使用项目随附真实快照，不上抛 500。"""
    try:
        with httpx.Client(timeout=45, follow_redirects=True) as client:
            r = client.get(CELESTRAK, params={"GROUP": group.upper(), "FORMAT": "TLE"})
            r.raise_for_status()
            if "1 25544" not in r.text and "1 " not in r.text:
                raise ValueError("CelesTrak 返回格式异常")
            (DATA_DIR / GROUP_FILES.get(group, "active.tle")).write_text(r.text, encoding="utf-8")
        records = read_tle_text(group)
        ingest_tle(records)
        log_collection(f"tle:{group}", "online", "CelesTrak 在线刷新成功", len(records))
        return {"source": "celestrak", "count": len(records), "degraded": False}
    except Exception as exc:
        records = read_tle_text(group)
        ingest_tle(records)
        log_collection(f"tle:{group}", "degraded", str(exc), len(records))
        return {"source": "local-snapshot", "count": len(records), "degraded": True,
                "message": "CelesTrak 暂不可用，已加载本地真实 TLE 快照"}

def ingest_tle(records):
    catalog = load_catalog()
    now = utcnow()
    with db() as con:
        for r in records:
            c = catalog.get(r["norad_id"], {})
            con.execute("""INSERT INTO satellites
                (norad_id,name,intl_designator,object_type,owner,launch_date,period,inclination,apogee,perigee,
                 tle_line1,tle_line2,source_group,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(norad_id) DO UPDATE SET name=excluded.name,
                intl_designator=COALESCE(excluded.intl_designator,satellites.intl_designator),
                object_type=COALESCE(excluded.object_type,satellites.object_type),
                owner=COALESCE(excluded.owner,satellites.owner),
                launch_date=COALESCE(excluded.launch_date,satellites.launch_date),
                period=COALESCE(excluded.period,satellites.period),
                inclination=COALESCE(excluded.inclination,satellites.inclination),
                apogee=COALESCE(excluded.apogee,satellites.apogee),
                perigee=COALESCE(excluded.perigee,satellites.perigee),
                tle_line1=excluded.tle_line1,tle_line2=excluded.tle_line2,
                source_group=excluded.source_group,updated_at=excluded.updated_at""",
                (r["norad_id"], r["name"], c.get("OBJECT_ID"), c.get("OBJECT_TYPE"), c.get("OWNER"),
                 c.get("LAUNCH_DATE"), float(c["PERIOD"]) if c.get("PERIOD") else None,
                 float(c["INCLINATION"]) if c.get("INCLINATION") else None,
                 float(c["APOGEE"]) if c.get("APOGEE") else None,
                 float(c["PERIGEE"]) if c.get("PERIGEE") else None,
                 r["line1"], r["line2"], "active", now))

# 多卫星追踪配置：知名卫星列表
TRACKED_SATELLITES = {
    25544: {"name": "ISS (ZARYA)", "group": "stations", "color": "#00e4ff"},
    20580: {"name": "HST (Hubble)", "group": "stations", "color": "#a855f7"},
    28654: {"name": "NOAA-18", "group": "weather", "color": "#d4af37"},
    33591: {"name": "NOAA-19", "group": "weather", "color": "#f97316"},
    43013: {"name": "NOAA-20 (JPSS-1)", "group": "weather", "color": "#22c55e"},
    37849: {"name": "SUOMI NPP", "group": "weather", "color": "#06b6d4"},
}

async def fetch_satellite_position(norad_id: int):
    """获取单颗卫星实时位置"""
    def work():
        with httpx.Client(timeout=15) as client:
            r = client.get(f"https://api.wheretheiss.at/v1/satellites/{norad_id}")
            r.raise_for_status()
            return r.json()
    try:
        data = await asyncio.to_thread(cached, f"iss:{norad_id}", CACHE_TTL["iss"], work)
        return {
            "noradId": norad_id,
            "name": TRACKED_SATELLITES.get(norad_id, {}).get("name", f"SAT-{norad_id}"),
            "lat": data["latitude"],
            "lng": data["longitude"],
            "alt": data["altitude"],
            "velocity": data["velocity"],
            "visibility": data.get("visibility"),
            "footprint": data.get("footprint"),
            "observedAt": datetime.fromtimestamp(data["timestamp"], timezone.utc).isoformat(),
            "degraded": False,
            "color": TRACKED_SATELLITES.get(norad_id, {}).get("color", "#00e4ff"),
        }
    except Exception as e:
        # 降级：用 SGP4 推算
        return await asyncio.to_thread(local_satellite_position, norad_id)

def local_satellite_position(norad_id: int):
    """SGP4 本地推算任意卫星位置"""
    from sgp4.api import Satrec, jday
    try:
        # 从数据库或本地文件找 TLE
        with db() as con:
            row = con.execute("SELECT tle_line1, tle_line2 FROM satellites WHERE norad_id=?", (norad_id,)).fetchone()
        if not row or not row["tle_line1"]:
            # 从本地 stations.tle 找
            records = read_tle_text("stations")
            sat = next((r for r in records if r["norad_id"] == norad_id), None)
            if not sat:
                raise ValueError(f"No TLE for {norad_id}")
            line1, line2 = sat["line1"], sat["line2"]
        else:
            line1, line2 = row["tle_line1"], row["tle_line2"]
        
        sat = Satrec.twoline2rv(line1, line2)
        now = datetime.now(timezone.utc)
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond / 1e6)
        e, r, v = sat.sgp4(jd, fr)
        if e != 0:
            raise ValueError(f"SGP4 error {e}")
        
        from math import atan2, degrees, sqrt
        jd2000 = 2451545.0
        d = jd + fr - jd2000
        gmst = (18.697374558 + 24.06570982441908 * d) % 24
        lng = ((degrees(atan2(r[1], r[0])) - gmst * 15 + 180) % 360) - 180
        lat = degrees(atan2(r[2], sqrt(r[0]**2 + r[1]**2)))
        alt = sqrt(sum(x*x for x in r)) - 6378.137
        velocity = sqrt(sum(x*x for x in v)) * 3600
        
        return {
            "noradId": norad_id,
            "name": TRACKED_SATELLITES.get(norad_id, {}).get("name", f"SAT-{norad_id}"),
            "lat": lat, "lng": lng, "alt": alt, "velocity": velocity,
            "observedAt": now.isoformat(),
            "degraded": True,
            "message": "SGP4 推算",
            "color": TRACKED_SATELLITES.get(norad_id, {}).get("color", "#00e4ff"),
        }
    except Exception as e:
        return {
            "noradId": norad_id,
            "name": TRACKED_SATELLITES.get(norad_id, {}).get("name", f"SAT-{norad_id}"),
            "lat": 0, "lng": 0, "alt": 0, "velocity": 0,
            "degraded": True,
            "message": f"推算失败: {str(e)}",
            "color": "#666",
        }

async def fetch_all_tracked():
    """并发获取所有追踪卫星位置"""
    tasks = [fetch_satellite_position(nid) for nid in TRACKED_SATELLITES]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    positions = []
    for r in results:
        if isinstance(r, dict):
            positions.append(r)
    return positions

async def fetch_iss():
    def work():
        with httpx.Client(timeout=15) as client:
            r = client.get(ISS_URL)
            r.raise_for_status()
            return r.json()
    data = await asyncio.to_thread(cached, "iss", CACHE_TTL["iss"], work)
    # 只有真实新数据才写历史，降级数据也保留来源提示
    with db() as con:
        last = con.execute("SELECT observed_at FROM iss_positions ORDER BY id DESC LIMIT 1").fetchone()
        observed = datetime.fromtimestamp(data["timestamp"], timezone.utc).isoformat()
        if not last or last["observed_at"] != observed:
            con.execute("""INSERT INTO iss_positions
                (norad_id,latitude,longitude,altitude,velocity,visibility,observed_at,created_at)
                VALUES(25544,?,?,?,?,?,?,?)""",
                (data["latitude"], data["longitude"], data["altitude"], data["velocity"],
                 data.get("visibility"), observed, utcnow()))
    return {"noradId": 25544, "name": data.get("name", "iss").upper(), "lat": data["latitude"],
            "lng": data["longitude"], "alt": data["altitude"], "velocity": data["velocity"],
            "visibility": data.get("visibility"), "footprint": data.get("footprint"),
            "observedAt": observed, "degraded": data.get("degraded", False),
            "message": data.get("message")}

def local_iss():
    """从随附真实 TLE 用 SGP4 推算；外部接口失败时不使用编造的固定坐标。"""
    from sgp4.api import Satrec, jday
    iss = next(r for r in read_tle_text("stations") if r["norad_id"] == 25544)
    sat = Satrec.twoline2rv(iss["line1"], iss["line2"])
    now = datetime.now(timezone.utc)
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute,
                  now.second + now.microsecond / 1e6)
    e, r, v = sat.sgp4(jd, fr)
    if e != 0:
        raise ExternalServiceError(f"SGP4 error {e}")
    from math import atan2, degrees, sqrt
    jd2000 = 2451545.0
    d = jd + fr - jd2000
    gmst = (18.697374558 + 24.06570982441908 * d) % 24
    lng = ((degrees(atan2(r[1], r[0])) - gmst * 15 + 180) % 360) - 180
    lat = degrees(atan2(r[2], sqrt(r[0]**2 + r[1]**2)))
    alt = sqrt(sum(x*x for x in r)) - 6378.137
    velocity = sqrt(sum(x*x for x in v)) * 3600
    return {"noradId": 25544, "name": "ISS (ZARYA)", "lat": lat, "lng": lng, "alt": alt,
            "velocity": velocity, "observedAt": now.isoformat(), "degraded": True,
            "message": "ISS API 暂不可用，位置由真实 TLE + SGP4 在服务端推算"}

async def iss_with_fallback():
    try:
        return await fetch_iss()
    except Exception as exc:
        log_collection("iss", "degraded", str(exc))
        return await asyncio.to_thread(local_iss)

def refresh_space_weather():
    try:
        with httpx.Client(timeout=20) as client:
            r = client.get(KP_URL)
            r.raise_for_status()
            raw = r.json()
            (DATA_DIR / "kp_sample.json").write_text(json.dumps(raw), encoding="utf-8")
        status = "online"
    except Exception:
        raw = json.loads((DATA_DIR / "kp_sample.json").read_text(encoding="utf-8"))
        status = "degraded"
    rows = raw[1:] if isinstance(raw, list) and raw and isinstance(raw[0], list) else raw
    with db() as con:
        for x in rows[-72:]:
            kp = float(x.get("Kp", 0))
            level = "强地磁暴" if kp >= 7 else "地磁暴" if kp >= 5 else "活跃" if kp >= 4 else "平静"
            con.execute("INSERT OR REPLACE INTO space_weather(time_tag,kp,level,created_at) VALUES(?,?,?,?)",
                        (x["time_tag"], kp, level, utcnow()))
    log_collection("space-weather", status, "NOAA SWPC Kp", len(rows))
    return len(rows)
