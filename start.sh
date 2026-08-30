#!/bin/bash
# 在 Zeabur 上启动时确保数据库目录存在

mkdir -p /data
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
