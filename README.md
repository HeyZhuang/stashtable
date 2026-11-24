# 星轨 · 卫星数据可视化大屏系统

前后端交互版 v3.0。真实 CelesTrak 在轨目录 + ISS 实时位置 + NOAA 空间天气，FastAPI / SQLite / WebSocket / Vue 3 / ECharts / Three.js。

## 已实现

- 登录 JWT 鉴权；未登录业务 API 与 WebSocket 均拒绝
- CelesTrak TLE、SatCat 目录后端采集；2 小时定时刷新
- ISS 位置 10 秒刷新并 WebSocket 推送；历史位置持久化
- 外部故障：优先最近缓存；ISS 无缓存时用**真实 TLE + SGP4** 在服务端推算，不返回固定假坐标
- SQLite 5 张业务表（卫星、ISS 历史、空间天气、观测记录、采集日志），外键与索引齐全
- 卫星分页/关键词/分组查询；观测记录 POST 写入并回查
- 轨道分布、运营方占比、发射趋势、Kp 空间天气聚合接口
- 1920×1080 基准等比缩放，ECharts 4 图 + Three.js 地球，断线 3 秒自动重连与降级提示
- Nginx 同源代理 `/api` 和 `/ws`，前端无第三方密钥

> 三维地球的大陆纹理由本地 Canvas 绘制，用于课程大屏视觉表达，**不是 GIS 精确地图**；实时 ISS 经纬度来自真实接口/TLE。发射趋势图统计的是“当前在轨目录中各月发射的目标数”，不等于当月全球全部发射次数。

## 一键启动（推荐）

要求 Docker 与 Docker Compose。

```bash
cp backend/.env.example backend/.env
# 修改后台密码、JWT Secret；NASA Key 可选，本版本核心大屏不依赖它
docker compose up --build -d
```

打开 `http://localhost:8080`。**登录使用数字藏经阁（LLMOps）邮箱账号**，内置演示账号已移除，请配置 `backend/.env` 中的 `SATDASH_SECRET` 为生产安全值。

```bash
docker compose ps       # 查看状态
docker compose logs -f  # 查看日志
docker compose down     # 停止（数据卷保留）
```

## 本地开发

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000

cd frontend
npm ci
# vite.config.js 的 proxy 改成 http://127.0.0.1:8000
npm run dev
```

后端 OpenAPI：`http://localhost:8000/docs`。

## 目录

```
backend/app/main.py                  生命周期、定时任务、WebSocket
backend/app/routers/api.py           登录、分页、写入、聚合 API
backend/app/services/collector.py    第三方代理、缓存、容错、SGP4
backend/app/database.py              SQLite 模型、索引、外键
backend/acceptance.py                真实接口验收脚本
frontend/src/App.vue                 大屏与交互
frontend/src/components/Earth.vue    Three.js 地球与实时 ISS 标记
frontend/src/components/VChart.vue   ECharts 生命周期封装
frontend/nginx.conf                  同源 HTTP / WebSocket 反向代理
```

## 验收

服务运行后：

```bash
BASE=http://127.0.0.1:8000 DB=./backend/data/satdash.db \
  .venv/bin/python backend/acceptance.py
```

本次本机实测：**后端 13/13 通过**；11,776 个在轨目标入库；WebSocket 收到真实 ISS 经纬度；浏览器端 5 个 Canvas、8 行卫星目录、观测写入回查正常；1920×1080 页面 `scrollWidth/scrollHeight = 1920/1080`，控制台无错误。

## 分工建议

- 前端：大屏布局与等比缩放、ECharts、Three.js、WebSocket 重连
- 后端：第三方代理/缓存、聚合 SQL、JWT、定时任务、WebSocket
- 统筹：数据库、联调、部署、测试记录、答辩 PPT

## 安全说明

- 所有第三方请求由后端发出，密钥仅来自后端环境变量。
- 本地课程演示采用 WebSocket URL Token；公网生产建议改为 Secure HttpOnly Cookie、CSRF 防护、登录限流与 HTTPS。
- SQLite 适合课程与单实例部署；多人高并发可平滑换 PostgreSQL/MySQL，Redis 可替换当前进程内 TTL 缓存。
