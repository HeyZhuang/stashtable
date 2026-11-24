from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from ..auth import create_token, require_user, llmops_login
from ..config import USE_LLMOPS_AUTH
from ..database import db, utcnow
from ..services.collector import refresh_tle, iss_with_fallback
import asyncio
import httpx

router = APIRouter(prefix="/api")

class LoginBody(BaseModel):
    email: str = Field(default="", description="LLMOps 邮箱账号")
    password: str = Field(default="", description="密码")
    # 兼容前端旧字段名：username 也按邮箱处理（纯邮箱体系）
    username: str = Field(default="", description="兼容字段，按邮箱处理")

@router.post("/auth/login")
async def login(body: LoginBody):
    """统一登录入口：仅支持 LLMOps 邮箱账号（内置 admin 已移除）"""
    if not USE_LLMOPS_AUTH:
        raise HTTPException(status_code=503, detail={"message": "统一认证服务未启用", "code": "AUTH_DISABLED"})
    email = (body.email or body.username).strip()
    if not email or not body.password:
        raise HTTPException(status_code=400, detail={"message": "请提供邮箱和密码", "code": "MISSING_CREDENTIALS"})
    if "@" not in email:
        raise HTTPException(status_code=400, detail={"message": "仅支持邮箱账号登录", "code": "EMAIL_REQUIRED"})
    result = await llmops_login(email, body.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail={"message": result["message"], "code": "LLMOPS_AUTH_FAILED"})
    # 身份已由 LLMOps 验证通过；用 satdash 本地 SECRET 签发统一 token（API + WS 共用，可被 require_user 验证）
    token = create_token(email)
    return {
        "token": token,
        "localToken": token,
        "tokenType": "Bearer",
        "expiresIn": 28800,
        "user": {
            "username": email,
            "displayName": result["user"].get("name") or email.split("@")[0],
            "email": email,
            "avatar": result["user"].get("avatar", ""),
            "source": "llmops"
        }
    }

@router.get("/dashboard/summary")
def summary(_=Depends(require_user)):
    with db() as con:
        total = con.execute("SELECT COUNT(*) n FROM satellites WHERE source_group='active'").fetchone()["n"]
        groups = con.execute("SELECT COUNT(DISTINCT source_group) n FROM satellites").fetchone()["n"]
        countries = con.execute("SELECT COUNT(DISTINCT owner) n FROM satellites WHERE owner IS NOT NULL AND owner!=''").fetchone()["n"]
        weather = con.execute("SELECT * FROM space_weather ORDER BY time_tag DESC LIMIT 1").fetchone()
        recent = con.execute("SELECT * FROM collection_logs ORDER BY id DESC LIMIT 6").fetchall()
        history = con.execute("SELECT COUNT(*) n FROM iss_positions").fetchone()["n"]
        active = con.execute("SELECT COUNT(*) n FROM satellites WHERE tle_line1 IS NOT NULL").fetchone()["n"]
    kp = weather["kp"] if weather else 0
    return {"total": total, "active": active, "groups": groups, "countries": countries,
            "issHistory": history, "spaceWeather": {"kp": kp, "level": weather["level"] if weather else "暂无",
            "time": weather["time_tag"] if weather else None},
            "collections": [dict(x) for x in recent], "updatedAt": utcnow()}

@router.get("/dashboard/orbit-distribution")
def orbit_distribution(_=Depends(require_user)):
    with db() as con:
        rows = con.execute("SELECT apogee,perigee,inclination FROM satellites WHERE source_group='active'").fetchall()
    result = {"LEO": 0, "MEO": 0, "GEO": 0, "HEO": 0}
    for r in rows:
        apo, per = r["apogee"] or 0, r["perigee"] or 0
        inc = r["inclination"] or 0
        if apo and per and apo - per > 1000 and apo > 10000:
            result["HEO"] += 1
        elif 35700 <= apo <= 35900 and abs(inc) < 5:
            result["GEO"] += 1
        elif apo < 2000 or (apo == 0 and per == 0):
            result["LEO"] += 1
        else:
            result["MEO"] += 1
    return {"items": [{"name": k, "value": v} for k, v in result.items()], "updatedAt": utcnow()}

@router.get("/dashboard/launch-trend")
def launch_trend(years: int = Query(5, ge=1, le=20), _=Depends(require_user)):
    # 国际标识符（TLE line1 第10-17位）前两位为发射年份，YY>=57 归 19YY，否则 20YY
    with db() as con:
        rows = con.execute("""SELECT
                CASE WHEN CAST(substr(tle_line1,10,2) AS INTEGER) >= 57
                     THEN 1900 + CAST(substr(tle_line1,10,2) AS INTEGER)
                     ELSE 2000 + CAST(substr(tle_line1,10,2) AS INTEGER)
                END AS yr, COUNT(*) value FROM satellites
            WHERE tle_line1 IS NOT NULL AND length(tle_line1)>=17
            GROUP BY yr ORDER BY yr DESC LIMIT ?""", (years,)).fetchall()
    items = [{"year": r["yr"], "month": str(r["yr"]), "value": r["value"]} for r in reversed(rows)]
    return {"years": years, "items": items, "note": "基于在轨目录 TLE 国际标识符统计的发射年份分布（非当月全部发射次数）"}

@router.get("/dashboard/countries")
def countries(_=Depends(require_user)):
    with db() as con:
        rows = con.execute("""SELECT COALESCE(NULLIF(owner,''),'UNKNOWN') name,COUNT(*) value FROM satellites
            WHERE source_group='active' GROUP BY owner ORDER BY value DESC LIMIT 8""").fetchall()
    return {"items": [dict(r) for r in rows]}

@router.get("/dashboard/weather-trend")
def weather_trend(_=Depends(require_user)):
    with db() as con:
        rows = con.execute("SELECT time_tag,kp,level FROM space_weather ORDER BY time_tag DESC LIMIT 24").fetchall()
    return {"items": [{"time": r["time_tag"], "kp": r["kp"], "level": r["level"]} for r in reversed(rows)]}

@router.get("/satellites")
def satellites(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
               keyword: str = "", group: str = "active", _=Depends(require_user)):
    where, params = "WHERE 1=1", []
    if keyword.strip():
        where += " AND (name LIKE ? OR CAST(norad_id AS TEXT) LIKE ? OR owner LIKE ?)"
        kw = f"%{keyword.strip()}%"
        params.extend([kw, kw, kw])
    if group != "all":
        where += " AND source_group=?"
        params.append(group)
    with db() as con:
        total = con.execute(f"SELECT COUNT(*) n FROM satellites {where}", params).fetchone()["n"]
        rows = con.execute(f"""SELECT norad_id,name,intl_designator,owner,launch_date,inclination,apogee,perigee,
            source_group,updated_at FROM satellites {where} ORDER BY norad_id LIMIT ? OFFSET ?""",
            params + [size, (page-1)*size]).fetchall()
    return {"total": total, "page": page, "size": size,
            "list": [{"noradId": r["norad_id"], "name": r["name"], "intlDesignator": r["intl_designator"],
                      "owner": r["owner"], "launchDate": r["launch_date"], "inclination": r["inclination"],
                      "apogee": r["apogee"], "perigee": r["perigee"], "group": r["source_group"],
                      "updatedAt": r["updated_at"]} for r in rows]}

@router.get("/satellites/tracked")
async def tracked_satellites(_=Depends(require_user)):
    """获取所有追踪卫星的实时位置"""
    from ..services.collector import fetch_all_tracked
    positions = await fetch_all_tracked()
    return {"items": positions, "count": len(positions), "updatedAt": utcnow()}

@router.get("/satellites/tracked/list")
def tracked_list(_=Depends(require_user)):
    """获取追踪卫星配置列表"""
    from ..services.collector import TRACKED_SATELLITES
    return {"items": [{"noradId": k, **v} for k, v in TRACKED_SATELLITES.items()]}

@router.get("/satellites/{norad_id}")
def satellite_detail(norad_id: int, _=Depends(require_user)):
    with db() as con:
        r = con.execute("SELECT * FROM satellites WHERE norad_id=?", (norad_id,)).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail={"message": "卫星不存在"})
    return dict(r)

class ObservationBody(BaseModel):
    satelliteId: int = Field(..., description="NORAD 编目号")
    observerName: str = Field(..., min_length=1, max_length=40)
    note: str = Field(..., min_length=2, max_length=500)

@router.post("/observations", status_code=201)
def create_observation(body: ObservationBody, user=Depends(require_user)):
    with db() as con:
        if not con.execute("SELECT 1 FROM satellites WHERE norad_id=?", (body.satelliteId,)).fetchone():
            raise HTTPException(status_code=422, detail={"message": "该 NORAD 编目号不在卫星目录中"})
        cur = con.execute("INSERT INTO observations(satellite_id,observer_name,note,created_at) VALUES(?,?,?,?)",
                          (body.satelliteId, body.observerName, body.note, utcnow()))
        row = con.execute("""SELECT o.*,s.name satellite_name FROM observations o
            JOIN satellites s ON s.norad_id=o.satellite_id WHERE o.id=?""", (cur.lastrowid,)).fetchone()
    return {"item": dict(row), "message": "观测记录已持久化，可回查"}

@router.get("/observations")
def observations(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=50), _=Depends(require_user)):
    with db() as con:
        total = con.execute("SELECT COUNT(*) n FROM observations").fetchone()["n"]
        rows = con.execute("""SELECT o.*,s.name satellite_name FROM observations o
            JOIN satellites s ON s.norad_id=o.satellite_id ORDER BY o.id DESC LIMIT ? OFFSET ?""",
            (size, (page-1)*size)).fetchall()
    return {"total": total, "list": [dict(r) for r in rows]}

@router.get("/iss/history")
def iss_history(limit: int = Query(60, ge=1, le=500), _=Depends(require_user)):
    with db() as con:
        rows = con.execute("""SELECT latitude,longitude,altitude,velocity,observed_at FROM iss_positions
            ORDER BY id DESC LIMIT ?""", (limit,)).fetchall()
    return {"items": [dict(r) for r in reversed(rows)]}

@router.post("/admin/refresh-tle")
async def admin_refresh(group: str = "active", _=Depends(require_user)):
    return await asyncio.to_thread(refresh_tle, group)

# ===== 历史轨迹回放 =====
@router.get("/iss/history/range")
def iss_history_range(
    start: str = Query(..., description="开始时间 ISO格式"),
    end: str = Query(..., description="结束时间 ISO格式"),
    limit: int = Query(500, ge=1, le=2000),
    _=Depends(require_user)
):
    """按时间范围查询ISS历史轨迹（用于回放）"""
    with db() as con:
        rows = con.execute("""
            SELECT latitude, longitude, altitude, velocity, visibility, observed_at
            FROM iss_positions
            WHERE observed_at >= ? AND observed_at <= ?
            ORDER BY observed_at ASC LIMIT ?
        """, (start, end, limit)).fetchall()
    return {"items": [dict(r) for r in rows], "count": len(rows)}

# ===== 每日天文一图（APOD）=====
@router.get("/nasa/apod")
async def nasa_apod(_=Depends(require_user)):
    """获取NASA每日天文一图（多源兜底：API → 官方页面抓图 → 内置图）"""
    from ..config import NASA_API_KEY
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        # 源1：官方 API
        try:
            resp = await client.get(
                "https://api.nasa.gov/planetary/apod",
                params={"api_key": NASA_API_KEY},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("url"):
                    return {
                        "title": data.get("title"),
                        "explanation": data.get("explanation"),
                        "url": data.get("url"),
                        "hdurl": data.get("hdurl"),
                        "mediaType": data.get("media_type"),
                        "date": data.get("date"),
                        "copyright": data.get("copyright", ""),
                        "source": "nasa-api",
                    }
        except Exception:
            pass

        # 源2：官方 APOD 页面抓今日图（science.nasa.gov）
        try:
            resp = await client.get("https://apod.nasa.gov/apod/astropix.html")
            if resp.status_code == 200:
                html = resp.text
                import re
                # 抓所有图片（跳过 logo 和小缩略图，优先大图）
                imgs = re.findall(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', html)
                big = [(u, a) for u, a in imgs
                       if "logo" not in u.lower()
                       and ("w=1024" in u or "w=1200" in u or "w=1600" in u or "w=1920" in u or "uploads" in u.lower())
                       and "?w=150" not in u]
                if not big:
                    big = [(u, a) for u, a in imgs if "logo" not in u.lower()]
                if big:
                    url, alt = big[0]
                    if url.startswith("//"):
                        url = "https:" + url
                    # 去掉查询参数里的小尺寸限制
                    url = re.sub(r'\?w=\d+.*$', '?w=1024', url)
                    return {
                        "title": (alt.strip() or "NASA 每日天文一图")[:80],
                        "explanation": "来自 NASA APOD 官方页面",
                        "url": url,
                        "mediaType": "image",
                        "date": utcnow()[:10],
                        "source": "nasa-page",
                    }
        except Exception:
            pass

        return {"error": "APOD暂不可用（多源失败）", "degraded": True}

# ===== 数据导出 =====
@router.get("/export/satellites/csv")
def export_satellites_csv(
    group: str = "active",
    _=Depends(require_user)
):
    """导出卫星目录CSV"""
    import csv
    import io
    with db() as con:
        rows = con.execute("""
            SELECT norad_id, name, intl_designator, owner, launch_date,
                   inclination, apogee, perigee, source_group, updated_at
            FROM satellites WHERE source_group=? ORDER BY norad_id
        """, (group,)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["NORAD_ID", "Name", "IntlDesignator", "Owner", "LaunchDate",
                     "Inclination", "Apogee(km)", "Perigee(km)", "Group", "UpdatedAt"])
    for r in rows:
        writer.writerow([r["norad_id"], r["name"], r["intl_designator"], r["owner"],
                        r["launch_date"], r["inclination"], r["apogee"], r["perigee"],
                        r["source_group"], r["updated_at"]])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=satellites_{group}_{utcnow()[:10]}.csv"}
    )

@router.get("/export/observations/csv")
def export_observations_csv(_=Depends(require_user)):
    """导出观测记录CSV"""
    import csv
    import io
    with db() as con:
        rows = con.execute("""
            SELECT o.id, o.satellite_id, s.name as satellite_name,
                   o.observer_name, o.note, o.created_at
            FROM observations o JOIN satellites s ON s.norad_id=o.satellite_id
            ORDER BY o.id DESC
        """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "SatelliteID", "SatelliteName", "Observer", "Note", "CreatedAt"])
    for r in rows:
        writer.writerow([r["id"], r["satellite_id"], r["satellite_name"],
                        r["observer_name"], r["note"], r["created_at"]])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=observations_{utcnow()[:10]}.csv"}
    )
