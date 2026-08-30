from fastmcp import FastMCP
from typing import Optional, List
import json

from app.services.memory_service import get_memory_service
from app.models.memory import MemoryCreate

# 创建 FastMCP 实例
mcp = FastMCP(
    name="memory-system",
    version="1.0.0",
    description="AI 长期记忆系统 MCP 服务"
)

@mcp.tool()
async def remember(
    content: str,
    layer: str = "long",
    memory_type: str = "fact",
    tags: List[str] = [],
    valence: float = 0.0,
    arousal: float = 0.0,
    unresolved: bool = False,
    event_date: Optional[str] = None,
) -> dict:
    """
    存储一条记忆。
    
    Args:
        content: 记忆内容
        layer: 层级 (core / long / short / consciousness)
        memory_type: 类型 (fact / event / unresolved / date / consciousness)
        tags: 标签列表
        valence: 情感效价 -1.0~1.0
        arousal: 情绪唤醒度 0.0~1.0
        unresolved: 是否未完成
        event_date: 事件日期 (YYYY-MM-DD)
    
    Returns:
        包含记忆 ID 和状态的字典
    """
    try:
        service = get_memory_service()
        
        memory = MemoryCreate(
            content=content,
            tags=tags,
            layer=layer,
            memory_type=memory_type,
            event_date=event_date,
            valence=valence,
            arousal=arousal,
            unresolved=unresolved
        )
        
        result = await service.create_memory(memory)
        
        if result:
            return {
                "success": True,
                "id": result.id,
                "content": result.content,
                "layer": result.layer,
                "unresolved": result.unresolved,
                "message": f"记忆已保存 (ID: {result.id})"
            }
        else:
            return {
                "success": False,
                "error": "保存记忆失败"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
async def recall(
    query: str,
    limit: int = 5,
    include_core: bool = True
) -> dict:
    """
    召回相关记忆。
    
    Args:
        query: 查询文本
        limit: 返回数量 (1-20)
        include_core: 是否包含核心记忆
    
    Returns:
        包含记忆列表和统计信息的字典
    """
    try:
        service = get_memory_service()
        
        limit = max(1, min(20, limit))
        
        result = await service.recall(query, limit, include_core)
        
        # 格式化返回（不包含 embedding）
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
                "pinned": mem.pinned,
                "created_at": mem.created_at
            })
        
        return {
            "success": True,
            "memories": memories,
            "recalled_count": result.get("recalled_count", 0),
            "core_count": result.get("core_count", 0),
            "latency_ms": result.get("latency_ms", 0)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "memories": []
        }

@mcp.tool()
async def resolve(memory_id: str) -> dict:
    """
    将一条记忆标记为已解决（仅适用于 unresolved=True 的记忆）。
    
    Args:
        memory_id: 记忆 ID
    
    Returns:
        操作结果
    """
    try:
        service = get_memory_service()
        result = await service.resolve(memory_id)
        
        if result:
            return {
                "success": True,
                "id": result.id,
                "content": result.content,
                "unresolved": result.unresolved,
                "message": f"记忆 {memory_id} 已标记为已解决"
            }
        else:
            return {
                "success": False,
                "error": f"记忆 {memory_id} 不存在或已被标记为已解决"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
async def resume() -> dict:
    """
    唤醒时加载所有核心记忆（core 层级）。
    
    Returns:
        核心记忆列表
    """
    try:
        service = get_memory_service()
        results = await service.resume()
        
        memories = []
        for mem in results:
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
            "success": True,
            "memories": memories,
            "count": len(memories)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "memories": []
        }
