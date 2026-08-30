import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os
from app.config import get_settings

settings = get_settings()

# 确保数据库目录存在
db_dir = os.path.dirname(settings.database_path)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """获取数据库连接，启用 WAL 和外键约束"""
    async with aiosqlite.connect(settings.database_path) as db:
        # 启用 WAL 模式
        await db.execute("PRAGMA journal_mode=WAL")
        # 启用外键约束
        await db.execute("PRAGMA foreign_keys=ON")
        # 设置 busy_timeout，避免并发写入冲突
        await db.execute("PRAGMA busy_timeout=5000")
        yield db

async def init_db():
    """初始化数据库表"""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        
        # memories 表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                tags_json TEXT DEFAULT '[]',
                layer TEXT NOT NULL DEFAULT 'long',
                memory_type TEXT NOT NULL DEFAULT 'fact',
                event_date TEXT,
                event_time TEXT,
                timezone TEXT DEFAULT 'Asia/Shanghai',
                expires_at TEXT,
                weight REAL NOT NULL DEFAULT 1.0,
                decay_rate REAL NOT NULL,
                valence REAL NOT NULL DEFAULT 0.0,
                arousal REAL NOT NULL DEFAULT 0.0,
                pinned INTEGER NOT NULL DEFAULT 0,
                unresolved INTEGER NOT NULL DEFAULT 0,
                last_triggered_at TEXT,
                trigger_count INTEGER NOT NULL DEFAULT 0,
                embedding BLOB,
                source_candidate_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 索引
        await db.execute("CREATE INDEX IF NOT EXISTS idx_memories_layer ON memories(layer)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_memories_unresolved ON memories(unresolved)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON memories(expires_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_memories_pinned ON memories(pinned)")
        
        # memory_candidates 表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory_candidates (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                content TEXT NOT NULL,
                tags_json TEXT DEFAULT '[]',
                proposed_memory_type TEXT,
                proposed_layer TEXT,
                proposed_event_date TEXT,
                proposed_valence REAL DEFAULT 0.5,
                proposed_arousal REAL DEFAULT 0.0,
                proposed_unresolved INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.5,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        
        # memory_links 表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory_links (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
                target_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
                link_type TEXT NOT NULL DEFAULT 'relates_to',
                weight REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                UNIQUE(source_id, target_id, link_type)
            )
        """)
        
        # memory_recall_logs 表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory_recall_logs (
                id TEXT PRIMARY KEY,
                query_hash TEXT NOT NULL,
                keyword_hits INTEGER NOT NULL DEFAULT 0,
                semantic_hits INTEGER NOT NULL DEFAULT 0,
                result_count INTEGER NOT NULL DEFAULT 0,
                latency_ms REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        
        await db.commit()
