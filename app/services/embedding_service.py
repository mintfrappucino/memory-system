import httpx
import numpy as np
from typing import List, Optional
import hashlib
from app.config import get_settings

settings = get_settings()

class EmbeddingService:
    def __init__(self):
        self.api_key = settings.siliconflow_api_key
        self.base_url = settings.siliconflow_base_url
        self.model = settings.siliconflow_embedding_model
        self._cache: dict[str, List[float]] = {}
    
    def _get_cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    async def embed(self, text: str) -> Optional[List[float]]:
        """获取单个文本的向量"""
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = await self.embed_batch([text])
        if result and len(result) > 0:
            self._cache[cache_key] = result[0]
            return result[0]
        return None
    
    async def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """批量获取向量"""
        if not texts or not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "input": texts,
                        "encoding_format": "float"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # 提取向量
                embeddings = []
                for item in data.get("data", []):
                    embeddings.append(item.get("embedding", []))
                
                # 缓存
                for i, text in enumerate(texts):
                    if i < len(embeddings):
                        cache_key = self._get_cache_key(text)
                        self._cache[cache_key] = embeddings[i]
                
                return embeddings
        except Exception as e:
            print(f"[Embedding] 调用失败: {e}")
            return None
    
    def vector_to_bytes(self, vector: List[float]) -> bytes:
        """将向量转换为 bytes 存储"""
        arr = np.array(vector, dtype=np.float32)
        return arr.tobytes()
    
    def bytes_to_vector(self, data: bytes) -> List[float]:
        """从 bytes 恢复向量"""
        arr = np.frombuffer(data, dtype=np.float32)
        return arr.tolist()

# 单例
_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
