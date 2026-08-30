import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import get_settings
from app.database import init_db
from app.routes import health, memories, mcp

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[启动] 环境: {settings.environment}")
    print(f"[启动] 数据库路径: {settings.database_path}")
    await init_db()
    print("[启动] 数据库初始化完成")
    yield
    print("[关闭] 应用正在关闭...")

app = FastAPI(
    title="记忆系统 MCP 服务",
    description="为 AI 提供长期记忆能力的 MCP 服务",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(MCPAuthMiddleware)

# 注册路由
app.include_router(health.router)
app.include_router(memories.router)
app.include_router(mcp.router)  # MCP 端点用 FastAPI 路由实现

@app.get("/")
async def root():
    return {
        "service": "记忆系统 MCP 服务",
        "version": "1.0.0",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health",
            "memories": "/memories"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )
