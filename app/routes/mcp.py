from fastapi import APIRouter, Request
import json

router = APIRouter(prefix="/mcp", tags=["mcp"])

@router.get("/")
async def mcp_get():
    return {"message": "MCP endpoint is ready"}

@router.post("/")
async def mcp_post(request: Request):
    try:
        body = await request.json()
        print(f"收到请求: {json.dumps(body, ensure_ascii=False)}")
        
        method = body.get("method", "")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "memory-system", "version": "1.0.0"}
                }
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {"tools": []}
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32601, "message": f"未知方法: {method}"}
            }
    except Exception as e:
        return {"error": str(e)}
