from datetime import datetime, timedelta, timezone
import jwt
import httpx
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import SECRET, TOKEN_HOURS, LLMOPS_API_URL

bearer = HTTPBearer(auto_error=False)

def create_token(username):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": username, "iat": now, "exp": now + timedelta(hours=TOKEN_HOURS)},
                      SECRET, algorithm="HS256")

def require_user(credentials: HTTPAuthorizationCredentials = Depends(bearer),
                 token: str = Query("", description="URL 参数 token（用于 window.open 下载）")):
    if not credentials and not token:
        raise HTTPException(status_code=401, detail={"message": "请先登录", "code": "UNAUTHORIZED"})
    cred = credentials.credentials if credentials else token
    try:
        payload = jwt.decode(cred, SECRET, algorithms=["HS256"])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail={"message": "Token 无效或已过期", "code": "UNAUTHORIZED"})

async def verify_llmops_token(token: str) -> dict:
    """验证 LLMOps token 并返回用户信息"""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"{LLMOPS_API_URL}/api/account",
                headers={"Authorization": f"Bearer {token}"}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "success":
                    return data.get("data", {})
            return None
        except Exception:
            return None

async def llmops_login(email: str, password: str) -> dict:
    """调用 LLMOps 登录接口"""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                f"{LLMOPS_API_URL}/api/auth/password-login",
                json={"email": email, "password": password}
            )
            data = resp.json()
            if data.get("code") == "success":
                return {
                    "success": True,
                    "token": data["data"].get("token"),
                    "user": data["data"].get("user", {}),
                    "expire_at": data["data"].get("expire_at")
                }
            else:
                return {
                    "success": False,
                    "message": data.get("message", "登录失败")
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"LLMOps 服务连接失败: {str(e)}"
            }
