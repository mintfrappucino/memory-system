from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class MCPAuthMiddleware(BaseHTTPMiddleware):
    """MCP 请求认证中间件 - 已禁用"""
    
    async def dispatch(self, request: Request, call_next):
        # 完全跳过认证
        response = await call_next(request)
        return response
