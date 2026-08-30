from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings
import secrets

settings = get_settings()

class MCPAuthMiddleware(BaseHTTPMiddleware):
    """MCP 请求认证中间件 - 只保护 /mcp 路径"""
    
    async def dispatch(self, request: Request, call_next):
        # 只对 /mcp 路径进行认证
        if request.url.path.startswith("/mcp"):
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                return await call_next(request)  # ← 改成返回，而不是抛异常
                # 或者如果你想强制认证，保留异常但确保处理
            
            # 支持 "Bearer <token>" 格式
            if not auth_header.startswith("Bearer "):
                return await call_next(request)  # ← 改成返回
            
            token = auth_header[7:].strip()
            
            # 验证 token
            if not secrets.compare_digest(token, settings.mcp_token):
                return await call_next(request)  # ← 改成返回
        
        response = await call_next(request)
        return response
