import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import hashlib
import aiosqlite
import math

from app.database import get_db
from app.models.memory import MemoryCreate, MemoryResponse, MemoryUpdate, generate_id
from app.models.candidate import CandidateResponse
from app.services.embedding_service import get_embedding_service

# 层级衰减配置
LAYER_DECAY = {
    "core": 0.0,          # 不衰减
    "consciousness": 0.0, # 不衰减
    "long": 0.995,
    "short": 0.95
}

LAYER_FLOOR = {
    "core": 1.0,
    "consciousness": 1.0,
    "long": 0.30,
    "short": 0.05
}

LAYER_FACTOR = {
    "core": 1.00,
    "long": 1.00,
    "short": 1.05,
    "consciousness": 0.88
}

class MemoryService:
    
    async def create_memory(self, memory: MemoryCreate) -> Optional[MemoryResponse]:
        """创建一条新记忆"""
        now = datetime.now().isoformat()
        memory_id = memory.id or generate_id()
        
        # 确定衰减率
        decay_rate = LAYER_DECAY.get(memory.layer, 0.995)
        
        # 生成 embedding
        embedding_bytes = None
        if memory.content:
            emb_service = get_embedding_service()
            vector = await emb_service.embed(memory.content)
            if vector:
                embedding_bytes = emb_service.vector_to_bytes(vector)
        
        # 计算过期时间（短期待）
        expires_at = None
        if memory.layer == "short":
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        
        async with get_db() as db:
            await db.execute("""
                INSERT INTO memories (
                    id, content, tags_json, layer, memory_type,
                    event_date, event_time, timezone,
                    expires_at, weight, decay_rate,
                    valence, arousal, pinned, unresolved,
                    embedding, source_candidate_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                memory.content,
                json.dumps(memory.tags),
                memory.layer,
                memory.memory_type,
                memory.event_date,
                memory.event_time,
                memory.timezone,
                expires_at,
                memory.weight,
                decay_rate,
                memory.valence,
                memory.arousal,
                1 if memory.pinned else 0,
                1 if memory.unresolved else 0,
                embedding_bytes,
                memory.source_candidate_id,
                now,
                now
            ))
            await db.commit()
        
        return await self.get_memory(memory_id)
    
    async def get_memory(self, memory_id: str) -> Optional[MemoryResponse]:
        """获取单条记忆"""
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return self._row_to_response(row)
    
    async def get_all_memories(
        self,
        layer: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryResponse]:
        """获取记忆列表"""
        query = "SELECT * FROM memories WHERE 1=1"
        params = []
        
        if layer:
            query += " AND layer = ?"
            params.append(layer)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with get_db() as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_response(row) for row in rows]
    
    async def update_memory(
        self,
        memory_id: str,
        update: MemoryUpdate
    ) -> Optional[MemoryResponse]:
        """更新记忆"""
        # 先获取现有记忆
        existing = await self.get_memory(memory_id)
        if not existing:
            return None
        
        # 构建更新字段
        fields = []
        params = []
        now = datetime.now().isoformat()
        
        update_data = update.model_dump(exclude_none=True)
        
        for key, value in update_data.items():
            if key == "tags" and value is not None:
                fields.append("tags_json = ?")
                params.append(json.dumps(value))
            elif key == "pinned" and value is not None:
                fields.append("pinned = ?")
                params.append(1 if value else 0)
            elif key == "unresolved" and value is not None:
                fields.append("unresolved = ?")
                params.append(1 if value else 0)
            elif key in ["layer"] and value is not None:
                fields.append(f"{key} = ?")
                params.append(value)
                # 如果是 layer 变更，更新 decay_rate
                if key == "layer":
                    fields.append("decay_rate = ?")
                    params.append(LAYER_DECAY.get(value, 0.995))
                    # 如果改为 core，清除过期时间
                    if value == "core":
                        fields.append("expires_at = ?")
                        params.append(None)
            elif key == "content" and value is not None:
                fields.append("content = ?")
                params.append(value)
                # 内容变更，重新生成 embedding
                emb_service = get_embedding_service()
                vector = await emb_service.embed(value)
                if vector:
                    fields.append("embedding = ?")
                    params.append(emb_service.vector_to_bytes(vector))
            elif key in ["event_date", "event_time", "timezone", "weight", "valence", "arousal"]:
                fields.append(f"{key} = ?")
                params.append(value)
        
        if not fields:
            return existing
        
        fields.append("updated_at = ?")
        params.append(now)
        params.append(memory_id)
        
        async with get_db() as db:
            await db.execute(
                f"UPDATE memories SET {', '.join(fields)} WHERE id = ?",
                params
            )
            await db.commit()
        
        return await self.get_memory(memory_id)
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        async with get_db() as db:
            # 先检查是否存在
            async with db.execute("SELECT id FROM memories WHERE id = ?", (memory_id,)) as cursor:
                if not await cursor.fetchone():
                    return False
            
            # 删除（外键级联会删除关联的 links）
            await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            await db.commit()
            return True
    
    async def recall(
        self,
        query: str,
        limit: int = 5,
        include_core: bool = True
    ) -> Dict[str, Any]:
        """
        混合召回记忆
        P0 版本：使用简单的关键词匹配 + 语义匹配
        """
        start_time = datetime.now()
        
        # 1. 构建核心记忆池（始终包含）
        core_memories = []
        if include_core:
            async with get_db() as db:
                async with db.execute(
                    "SELECT * FROM memories WHERE layer = 'core' AND pinned = 1"
                ) as cursor:
                    rows = await cursor.fetchall()
                    core_memories = [self._row_to_response(row) for row in rows]
        
        # 2. 如果没有查询内容，只返回核心记忆
        if not query or not query.strip():
            return {
                "memories": core_memories,
                "recalled": [],
                "core_count": len(core_memories)
            }
        
        # 3. 获取所有非核心记忆（P0 简化版，数据量大时需要优化）
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM memories WHERE layer != 'core' OR pinned = 0"
            ) as cursor:
                rows = await cursor.fetchall()
                all_memories = [self._row_to_response(row) for row in rows]
        
        if not all_memories:
            return {
                "memories": core_memories,
                "recalled": [],
                "core_count": len(core_memories)
            }
        
        # 4. 生成查询向量
        emb_service = get_embedding_service()
        query_vector = await emb_service.embed(query)
        
        # 5. 计算分数
        query_lower = query.lower()
        query_bigrams = self._get_bigrams(query_lower)
        
        scored = []
        for mem in all_memories:
            # 5a. 词法分数
            lexical_score = self._compute_lexical_score(query_lower, query_bigrams, mem)
            
            # 5b. 语义分数
            semantic_score = 0.0
            if query_vector and mem.embedding:
                mem_vector = emb_service.bytes_to_vector(mem.embedding)
                semantic_score = self._cosine_similarity(query_vector, mem_vector)
            
            # 5c. 混合分数（P0 简化版）
            if lexical_score > 0 and semantic_score > 0:
                raw = 0.42 * lexical_score + 0.58 * semantic_score + 0.08
            elif semantic_score > 0:
                raw = 0.82 * semantic_score
            elif lexical_score > 0:
                raw = lexical_score
            else:
                continue
            
            # 加入层级因子
            layer_factor = LAYER_FACTOR.get(mem.layer, 1.0)
            
            # arousal 加成（最多 15%）
            arousal_bonus = 1.0 + 0.15 * mem.arousal
            
            # unresolved 加成
            unresolved_bonus = 1.08 if mem.unresolved else 1.0
            
            final_score = raw * layer_factor * arousal_bonus * unresolved_bonus
            
            # 记录命中类型
            keyword_hit = 1 if lexical_score > 0 else 0
            semantic_hit = 1 if semantic_score > 0 else 0
            
            scored.append({
                "memory": mem,
                "score": final_score,
                "lexical_score": lexical_score,
                "semantic_score": semantic_score,
                "keyword_hit": keyword_hit,
                "semantic_hit": semantic_hit
            })
        
        # 6. 按分数排序
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        # 7. 多样性筛选（P0 简化版）
        selected = []
        for item in scored[:min(len(scored), limit * 2)]:  # 先取 2 倍候选
            # 简单的去重：避免内容过于相似（P0 用简单的词法去重）
            is_duplicate = False
            for selected_item in selected:
                # 检查 bigram 重叠率
                mem1_bigrams = self._get_bigrams(item["memory"].content.lower())
                mem2_bigrams = self._get_bigrams(selected_item["memory"].content.lower())
                overlap = self._bigram_overlap(mem1_bigrams, mem2_bigrams)
                if overlap > 0.60:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                selected.append(item)
                if len(selected) >= limit:
                    break
        
        # 8. 更新触发状态（冷却：6 小时内只计一次）
        now_iso = datetime.now().isoformat()
        for item in selected[:limit]:
            await self._trigger_memory(item["memory"].id, now_iso)
        
        # 9. 记录召回日志
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        await self._log_recall(
            query,
            sum(1 for s in scored if s["keyword_hit"] > 0),
            sum(1 for s in scored if s["semantic_hit"] > 0),
            len(selected),
            elapsed
        )
        
        return {
            "memories": core_memories + [item["memory"] for item in selected],
            "recalled": [item["memory"] for item in selected],
            "core_count": len(core_memories),
            "recalled_count": len(selected),
            "latency_ms": elapsed
        }
    
    async def resolve(self, memory_id: str) -> Optional[MemoryResponse]:
        """标记记忆为已解决"""
        existing = await self.get_memory(memory_id)
        if not existing:
            return None
        
        # 只有 unresolved 的记忆才能被 resolve
        if not existing.unresolved:
            return existing
        
        update = MemoryUpdate(unresolved=False)
        return await self.update_memory(memory_id, update)
    
    async def resume(self) -> List[MemoryResponse]:
        """唤醒时加载核心记忆"""
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM memories WHERE layer = 'core' AND pinned = 1 ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_response(row) for row in rows]
    
    async def get_candidates(self, status: str = "pending") -> List[CandidateResponse]:
        """获取候选记忆"""
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM memory_candidates WHERE status = ? ORDER BY created_at DESC",
                (status,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_candidate_response(row) for row in rows]
    
    async def accept_candidate(self, candidate_id: str) -> Optional[MemoryResponse]:
        """接受候选记忆，转为正式记忆"""
        async with get_db() as db:
            # 获取候选
            async with db.execute(
                "SELECT * FROM memory_candidates WHERE id = ? AND status = 'pending'",
                (candidate_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
            
            # 更新状态
            await db.execute(
                "UPDATE memory_candidates SET status = 'accepted' WHERE id = ?",
                (candidate_id,)
            )
            await db.commit()
            
            # 创建正式记忆
            memory = MemoryCreate(
                content=row[2],  # content
                tags=json.loads(row[3]) if row[3] else [],
                layer=row[5] or "long",  # proposed_layer
                memory_type=row[4] or "fact",  # proposed_memory_type
                event_date=row[6],  # proposed_event_date
                valence=row[7] or 0.0,
                arousal=row[8] or 0.0,
                unresolved=bool(row[9] or 0),
                source_candidate_id=candidate_id
            )
            return await self.create_memory(memory)
    
    async def reject_candidate(self, candidate_id: str) -> bool:
        """拒绝候选记忆"""
        async with get_db() as db:
            result = await db.execute(
                "UPDATE memory_candidates SET status = 'rejected' WHERE id = ? AND status = 'pending'",
                (candidate_id,)
            )
            await db.commit()
            return result.rowcount > 0
    
    # === 辅助方法 ===
    
    def _get_bigrams(self, text: str) -> List[str]:
        """提取中文双字组"""
        if not text:
            return []
        return [text[i:i+2] for i in range(len(text)-1)]
    
    def _bigram_overlap(self, bg1: List[str], bg2: List[str]) -> float:
        """计算 bigram 重叠率"""
        if not bg1 or not bg2:
            return 0.0
        set1, set2 = set(bg1), set(bg2)
        overlap = len(set1 & set2)
        return overlap / min(len(set1), len(set2))
    
    def _compute_lexical_score(self, query: str, query_bigrams: List[str], memory) -> float:
        """计算词法匹配分数"""
        content_lower = memory.content.lower()
        
        # 完全匹配
        if query == content_lower:
            return 1.0
        
        # query 是 content 的子串
        if query in content_lower:
            return 0.85
        
        # bigram 匹配
        content_bigrams = self._get_bigrams(content_lower)
        overlap = self._bigram_overlap(query_bigrams, content_bigrams)
        if overlap > 0:
            return overlap * 0.65
        
        # Tag 匹配
        if memory.tags:
            for tag in memory.tags:
                if query in tag.lower() or tag.lower() in query:
                    return 0.72
        
        return 0.0
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    async def _trigger_memory(self, memory_id: str, now: str):
        """更新记忆的触发状态（6 小时冷却）"""
        async with get_db() as db:
            # 检查 6 小时内是否触发过
            six_hours_ago = (datetime.now() - timedelta(hours=6)).isoformat()
            async with db.execute(
                "SELECT last_triggered_at FROM memories WHERE id = ? AND last_triggered_at > ?",
                (memory_id, six_hours_ago)
            ) as cursor:
                if await cursor.fetchone():
                    return  # 冷却中，不更新
            
            await db.execute(
                "UPDATE memories SET last_triggered_at = ?, trigger_count = trigger_count + 1 WHERE id = ?",
                (now, memory_id)
            )
            await db.commit()
    
    async def _log_recall(self, query: str, keyword_hits: int, semantic_hits: int, result_count: int, latency_ms: float):
        """记录召回日志"""
        query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()[:16]
        async with get_db() as db:
            await db.execute(
                "INSERT INTO memory_recall_logs (id, query_hash, keyword_hits, semantic_hits, result_count, latency_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"log_{uuid.uuid4().hex[:12]}", query_hash, keyword_hits, semantic_hits, result_count, latency_ms, datetime.now().isoformat())
            )
            await db.commit()
    
    def _row_to_response(self, row) -> MemoryResponse:
        """将数据库行转换为 MemoryResponse"""
        return MemoryResponse(
            id=row[0],
            content=row[1],
            tags=json.loads(row[2]) if row[2] else [],
            layer=row[3],
            memory_type=row[4],
            event_date=row[5],
            event_time=row[6],
            timezone=row[7] or "Asia/Shanghai",
            expires_at=row[8],
            weight=row[9] or 1.0,
            decay_rate=row[10] or 0.995,
            valence=row[11] or 0.0,
            arousal=row[12] or 0.0,
            pinned=bool(row[13] or 0),
            unresolved=bool(row[14] or 0),
            last_triggered_at=row[15],
            trigger_count=row[16] or 0,
            created_at=row[19],
            updated_at=row[20],
            embedding=row[17]  # 保留但不用于 Response 展示
        )
    
    def _row_to_candidate_response(self, row) -> CandidateResponse:
        """将数据库行转换为 CandidateResponse"""
        return CandidateResponse(
            id=row[0],
            conversation_id=row[1],
            content=row[2],
            tags=json.loads(row[3]) if row[3] else [],
            proposed_memory_type=row[4],
            proposed_layer=row[5],
            proposed_event_date=row[6],
            proposed_valence=row[7] or 0.5,
            proposed_arousal=row[8] or 0.0,
            proposed_unresolved=bool(row[9] or 0),
            confidence=row[10] or 0.5,
            status=row[11],
            created_at=row[12]
        )

# 单例
_memory_service: Optional[MemoryService] = None

def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
