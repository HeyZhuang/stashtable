#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; fi
docker compose up --build -d
echo "大屏地址: http://localhost:8080  账号: admin / admin123"
