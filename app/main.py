import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import get_settings
from app.auth import MCPAuthMiddleware
from app.database import init_db
from app.routes import health, memories
from app.mcp.tools import mcp

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print(f"[启动] 环境: {settings.environment}")
    print(f"[启动] 数据库路径: {settings.database_path}")
    
    # 初始化数据库
    await init_db()
    print("[启动] 数据库初始化完成")
    
    yield
    
    print("[关闭] 应用正在关闭...")

# 创建 FastAPI 应用
app = FastAPI(
    title="记忆系统 MCP 服务",
    description="为 AI 提供长期记忆能力的 MCP 服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置（允许 Kelivo 跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议限定为 Kelivo 域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加 MCP 认证中间件（只保护 /mcp）
app.add_middleware(MCPAuthMiddleware)

# 注册路由
app.include_router(health.router)
app.include_router(memories.router)

# 挂载 FastMCP - 关键步骤
app.mount("/mcp", mcp.http_app())

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
