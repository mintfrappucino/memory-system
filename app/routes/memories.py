from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.services.memory_service import get_memory_service
from app.models.memory import MemoryUpdate

router = APIRouter(prefix="/memories", tags=["memories"])

@router.get("/")
async def list_memories(
    layer: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """获取记忆列表"""
    service = get_memory_service()
    memories = await service.get_all_memories(layer, limit, offset)
    return {
        "items": memories,
        "count": len(memories),
        "limit": limit,
        "offset": offset
    }

@router.get("/{memory_id}")
async def get_memory(memory_id: str):
    """获取单条记忆"""
    service = get_memory_service()
    memory = await service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return memory

@router.put("/{memory_id}")
async def update_memory(memory_id: str, update: MemoryUpdate):
    """更新记忆"""
    service = get_memory_service()
    result = await service.update_memory(memory_id, update)
    if not result:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return result

@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """删除记忆"""
    service = get_memory_service()
    success = await service.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"success": True, "id": memory_id}

@router.post("/{memory_id}/resolve")
async def resolve_memory(memory_id: str):
    """标记记忆为已解决"""
    service = get_memory_service()
    result = await service.resolve(memory_id)
    if not result:
        raise HTTPException(status_code=404, detail="记忆不存在或已解决")
    return {"success": True, "id": memory_id, "unresolved": False}
