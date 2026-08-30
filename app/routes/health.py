from fastapi import APIRouter, Response
import aiosqlite
from app.config import get_settings

router = APIRouter()
settings = get_settings()

@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "memory-system",
        "environment": settings.environment
    }

@router.get("/ready")
async def ready_check():
    """就绪检查 - 验证数据库可读写"""
    try:
        async with aiosqlite.connect(settings.database_path) as db:
            await db.execute("SELECT 1")
            row = await db.execute("SELECT 1")
            await row.fetchone()
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        return Response(
            status_code=503,
            content=f'{{"status": "not_ready", "error": "{str(e)}"}}'
        )
