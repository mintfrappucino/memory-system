from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
import json
import logging

from app.services.memory_service import get_memory_service
from app.models.memory import MemoryCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[dict] = None
    id: Optional[str] = None

@router.get("/")
async def mcp_get():
    """GET 请求返回服务信息（兼容 Kelivo 发现）"""
    return {
        "name": "memory-system",
        "version": "1.0.0",
        "description": "AI 长期记忆系统 MCP 服务",
        "protocol": "mcp",
        "capabilities": ["tools"]
    }

@router.post("/")
async def mcp_handler(request: MCPRequest):
    """
    MCP 端点 - 处理 Kelivo 的 MCP 协议请求
    """
    service = get_memory_service()
    method = request.method
    params = request.params or {}
    
    logger.info(f"MCP 请求: method={method}, id={request.id}")
    
    try:
        # 1. 初始化请求
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "memory-system",
                        "version": "1.0.0"
                    }
                }
            }
        
        # 2. 列出工具
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "tools": [
                        {
                            "name": "remember",
                            "description": "存储一条记忆",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string", "description": "记忆内容"},
                                    "layer": {"type": "string", "enum": ["core", "long", "short", "consciousness"]},
                                    "tags": {"type": "array", "items": {"type": "string"}},
                                    "unresolved": {"type": "boolean"}
                                },
                                "required": ["content"]
                            }
                        },
                        {
                            "name": "recall",
                            "description": "召回相关记忆",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "查询文本"},
                                    "limit": {"type": "integer", "description": "返回数量"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "resolve",
                            "description": "标记记忆为已解决",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "memory_id": {"type": "string", "description": "记忆ID"}
                                },
                                "required": ["memory_id"]
                            }
                        },
                        {
                            "name": "resume",
                            "description": "唤醒时加载核心记忆",
                            "inputSchema": {"type": "object", "properties": {}}
                        }
                    ]
                }
            }
        
        # 3. 调用工具
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            if tool_name == "remember":
                result = await service.create_memory(MemoryCreate(
                    content=tool_args.get("content", ""),
                    tags=tool_args.get("tags", []),
                    layer=tool_args.get("layer", "long"),
                    memory_type=tool_args.get("memory_type", "fact"),
                    event_date=tool_args.get("event_date"),
                    valence=tool_args.get("valence", 0.0),
                    arousal=tool_args.get("arousal", 0.0),
                    unresolved=tool_args.get("unresolved", False)
                ))
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "id": result.id if result else None,
                                "message": "记忆已保存" if result else "保存失败"
                            })
                        }]
                    }
                }
            
            elif tool_name == "recall":
                result = await service.recall(
                    query=tool_args.get("query", ""),
                    limit=tool_args.get("limit", 5),
                    include_core=tool_args.get("include_core", True)
                )
                memories = []
                for mem in result.get("memories", []):
                    memories.append({
                        "id": mem.id,
                        "content": mem.content,
                        "layer": mem.layer,
                        "memory_type": mem.memory_type,
                        "tags": mem.tags,
                        "valence": mem.valence,
                        "arousal": mem.arousal,
                        "unresolved": mem.unresolved,
                        "created_at": mem.created_at
                    })
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "memories": memories,
                                "count": len(memories)
                            })
                        }]
                    }
                }
            
            elif tool_name == "resolve":
                result = await service.resolve(tool_args.get("memory_id", ""))
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": bool(result),
                                "message": "已标记为已解决" if result else "操作失败"
                            })
                        }]
                    }
                }
            
            elif tool_name == "resume":
                result = await service.resume()
                memories = []
                for mem in result:
                    memories.append({
                        "id": mem.id,
                        "content": mem.content,
                        "layer": mem.layer,
                        "memory_type": mem.memory_type,
                        "tags": mem.tags,
                        "created_at": mem.created_at
                    })
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "memories": memories,
                                "count": len(memories)
                            })
                        }]
                    }
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": {
                        "code": -32601,
                        "message": f"未知工具: {tool_name}"
                    }
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32601,
                    "message": f"未知方法: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"MCP 处理异常: {str(e)}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32000,
                "message": str(e)
            }
        }
