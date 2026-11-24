import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("SATDASH_DATA_DIR", str(BASE_DIR / "data")))
DB_PATH = os.getenv("SATDASH_DB", str(DATA_DIR / "satdash.db"))
SECRET = os.getenv("SATDASH_SECRET", "course-design-local-secret")
ADMIN_USER = os.getenv("SATDASH_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("SATDASH_ADMIN_PASSWORD", "admin123")
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
TOKEN_HOURS = 8
# 秒：按题设 TLE 2 小时、ISS 10 秒、日更 1 天
CACHE_TTL = {"tle": 7200, "iss": 10, "summary": 300, "daily": 86400}
# LLMOps 统一认证（容器内访问宿主机用 host.docker.internal 或宿主机IP）
LLMOPS_API_URL = os.getenv("LLMOPS_API_URL", "http://host.docker.internal:80")
# 是否启用 LLMOps 统一登录（false 则回退到本地账号）
USE_LLMOPS_AUTH = os.getenv("USE_LLMOPS_AUTH", "true").lower() == "true"
