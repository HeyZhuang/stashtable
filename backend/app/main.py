import asyncio
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .config import ADMIN_USER, ADMIN_PASSWORD
from .database import init_db, log_collection, utcnow
from .routers.api import router
from .services.collector import refresh_tle, iss_with_fallback, refresh_space_weather

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("satdash")
clients = set()
scheduler = AsyncIOScheduler(timezone="UTC")

def schedule(loop, coro_fn):
    """把协程工厂函数提交到启动时保存的 FastAPI loop。
    每次触发新建协程，避免“协程对象只能 await 一次”导致定时任务第二次触发即失效。"""
    return lambda: asyncio.run_coroutine_threadsafe(coro_fn(), loop)

async def broadcast_iss():
    if not clients:
        # 没客户端时仍保留历史采集
        await iss_with_fallback()
        return
    # 并发获取所有追踪卫星
    from .services.collector import fetch_all_tracked
    positions = await fetch_all_tracked()
    data = {"type": "satellites", "items": positions, "serverTime": utcnow()}
    dead = []
    for ws in list(clients):
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # 首启从随附真实快照入库，不依赖外网；在线刷新由定时任务负责
    await asyncio.to_thread(refresh_tle, "active")
    await asyncio.to_thread(refresh_space_weather)
    await iss_with_fallback()
    loop = asyncio.get_running_loop()
    scheduler.add_job(schedule(loop, lambda: asyncio.to_thread(refresh_tle, "active")),
                      "interval", hours=2, id="tle-refresh", replace_existing=True)
    scheduler.add_job(schedule(loop, lambda: asyncio.to_thread(refresh_space_weather)),
                      "interval", hours=1, id="weather-refresh", replace_existing=True)
    scheduler.add_job(schedule(loop, broadcast_iss),
                      "interval", seconds=10, id="iss-realtime", replace_existing=True,
                      max_instances=1, coalesce=True)
    scheduler.start()
    logger.info("SatDash started; TLE=2h ISS=10s; admin=%s", ADMIN_USER)
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(title="卫星数据可视化大屏系统", version="3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "satdash-backend", "realtimeClients": len(clients)}

@app.websocket("/ws/realtime")
async def realtime(ws: WebSocket, token: str = Query(default="")):
    # 课程设计采用 URL token；正式生产建议 HttpOnly Cookie + CSRF 防护
    import jwt
    from .config import SECRET
    try:
        jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        await ws.close(code=4401, reason="Unauthorized")
        return
    await ws.accept()
    clients.add(ws)
    try:
        await ws.send_json({"type": "hello", "data": {"message": "实时通道已连接", "interval": 10}})
        await ws.send_json({"type": "iss", "data": await iss_with_fallback()})
        while True:
            # 支持心跳，也避免后端因不读取而误判连接状态
            text = await ws.receive_text()
            if text == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)

@app.exception_handler(Exception)
async def unhandled(request, exc):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": {"message": "服务暂时异常，请稍后重试", "code": "INTERNAL"}})
