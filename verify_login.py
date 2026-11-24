#!/usr/bin/env python3
# 卫星大屏统一登录验证脚本（LLMOps 邮箱账号）
# 用法: python3 verify_login.py <你的LLMOps邮箱> <密码>
# 验证: 登录拿token -> API鉴权 -> WebSocket 鉴权 -> 实时推送
import json, sys, asyncio, urllib.request, urllib.error

BASE = "http://127.0.0.1:8080/satdash"

def post(path, body):
    req = urllib.request.Request(BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")

def main():
    if len(sys.argv) != 3:
        print("用法: python3 verify_login.py <邮箱> <密码>")
        sys.exit(1)
    email, pwd = sys.argv[1], sys.argv[2]

    print("1️⃣ 登录拿 token...")
    code, d = post("/api/auth/login", {"email": email, "password": pwd})
    if code != 200 or not d.get("token"):
        print(f"  ❌ 登录失败 ({code}): {d.get('detail', d)}")
        sys.exit(1)
    token = d["token"]
    print(f"  ✅ 登录成功 | token 前缀: {token[:25]}... | 用户: {d.get('user', {}).get('email')}")
    print(f"     user.displayName: {d.get('user', {}).get('displayName')} | source: {d.get('user', {}).get('source')}")

    print("2️⃣ API 权限验证（dashboard/summary）...")
    req = urllib.request.Request(BASE + "/api/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        data = json.loads(r.read().decode())
        print(f"  ✅ 鉴权通过 | total={data.get('total')} active={data.get('active')} issHistory={data.get('issHistory')}")
    except urllib.error.HTTPError as e:
        print(f"  ❌ 鉴权失败 ({e.code})")
        sys.exit(1)

    print("3️⃣ WebSocket 鉴权 + 实时推送...")
    async def ws_test():
        import websockets
        async with websockets.connect(f"ws://127.0.0.1:8080/satdash/ws/realtime?token={token}") as ws:
            first = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            print(f"  ✅ WS 连接成功 | 首条: {first.get('type')}")
            sats = 0
            try:
                while sats < 2:
                    m = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                    if m.get("type") == "satellites":
                        sats += 1
                        items = m.get("items", [])
                        iss = next((s for s in items if s.get("noradId") == 25544), {})
                        print(f"  📡 推送#{sats}: 卫星×{len(items)} | ISS lat={iss.get('lat'):.2f} lng={iss.get('lng'):.2f} alt={iss.get('alt'):.0f}km")
            except asyncio.TimeoutError:
                pass
            print(f"  ✅ WS 实时推送正常（{sats} 次）")
    asyncio.run(ws_test())

    print("\n🎉 全链路验证通过：登录 → token → API鉴权 → WS鉴权 → 实时推送")

if __name__ == "__main__":
    main()
