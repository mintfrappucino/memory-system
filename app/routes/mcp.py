from fastapi import APIRouter
import json

router = APIRouter(prefix="/mcp", tags=["mcp"])

@router.get("/")
async def mcp_get():
    # 返回基础信息，让 Kelivo 知道服务存在
    return {"name": "memory-system", "version": "1.0.0"}

@router.post("/")
async def mcp_post(request: dict):
    # 打印收到的请求，便于排查
    print("收到请求:", json.dumps(request, ensure_ascii=False))
    # 返回最基础的 MCP 响应
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "result": {"tools": []}  # 暂时返回空工具列表
    }
