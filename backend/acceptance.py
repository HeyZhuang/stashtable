#!/usr/bin/env python3
"""对运行中的后端做端到端验收；默认 BASE=http://127.0.0.1:47237。"""
import asyncio, json, os, sqlite3, sys, urllib.request, urllib.error
import websockets

BASE = os.getenv("BASE", "http://127.0.0.1:47237")
results = []

def request(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail, flush=True)

status, login = request("/api/auth/login", "POST", {"username": "admin", "password": "admin123"})
token = login.get("token")
check("A-3 登录签发 Token", status == 200 and token)
status, body = request("/api/dashboard/summary")
check("A-3 未登录返回 401", status == 401, str(status))
status, summary = request("/api/dashboard/summary", token=token)
check("健康检查与汇总", status == 200 and summary["total"] > 1000, f"在轨={summary.get('total')}")
status, page = request("/api/satellites?page=2&size=20&keyword=ISS", token=token)
check("A-6 分页+关键词", status == 200 and "total" in page and "list" in page, f"total={page.get('total')} size={len(page.get('list',[]))}")
status, created = request("/api/observations", "POST", {"satelliteId": 25544, "observerName": "验收脚本", "note": "自动化验收：数据库写入并回查。"}, token)
check("数据写入", status == 201, str(created.get("item", {}).get("id")))
status, queried = request("/api/observations?page=1&size=10", token=token)
check("写入后回查", status == 200 and queried.get("total", 0) >= 1 and queried["list"][0]["note"] == "自动化验收：数据库写入并回查。")
for path in ("/api/dashboard/orbit-distribution", "/api/dashboard/launch-trend?months=12", "/api/dashboard/countries", "/api/dashboard/weather-trend"):
    status, body = request(path, token=token)
    check("聚合接口 " + path, status == 200 and body.get("items"), f"{len(body.get('items',[]))} 项")

async def ws_test():
    uri = BASE.replace("http", "ws") + "/ws/realtime?token=" + token
    async with websockets.connect(uri, open_timeout=20) as ws:
        hello = json.loads(await asyncio.wait_for(ws.recv(), 20))
        data = json.loads(await asyncio.wait_for(ws.recv(), 30))
        check("A-8 WebSocket 鉴权与推送", hello["type"] == "hello" and data["type"] == "iss" and abs(data["data"]["lat"]) <= 90,
              f"{data['data']['name']} lat={data['data']['lat']:.3f}")
    try:
        async with websockets.connect(BASE.replace("http", "ws") + "/ws/realtime?token=bad") as ws:
            await ws.recv()
        check("WebSocket 未登录拒绝", False)
    except Exception:
        check("WebSocket 未登录拒绝", True)
asyncio.run(ws_test())

con = sqlite3.connect(os.getenv("DB", "/root/satdash/backend/data/satdash.db"))
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
fks = con.execute("PRAGMA foreign_key_list(iss_positions)").fetchall()
indexes = con.execute("PRAGMA index_list(satellites)").fetchall()
check("A-2 至少三表+外键+索引", len(tables) >= 3 and fks and indexes, f"tables={tables}")
print(f"\n结果：{sum(x[1] for x in results)}/{len(results)} 通过")
sys.exit(0 if all(x[1] for x in results) else 1)
