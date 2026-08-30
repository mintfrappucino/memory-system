from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings

settings = get_settings()

class MCPAuthMiddleware(BaseHTTPMiddleware):
    """MCP 请求认证中间件 - 只保护 /mcp 路径"""
    
    async def dispatch(self, request: Request, call_next):
        # 只对 /mcp 路径进行认证
        if request.url.path.startswith("/mcp"):
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Authorization header"
                )
            
            # 支持 "Bearer <token>" 格式
            if not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Authorization format. Expected 'Bearer <token>'"
                )
            
            token = auth_header[7:].strip()
            
            # 使用 secrets.compare_digest 防止时序攻击
            import secrets
            if not secrets.compare_digest(token, settings.mcp_token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
        
        response = await call_next(request)
        return response
