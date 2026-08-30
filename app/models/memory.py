from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

class MemoryBase(BaseModel):
    content: str
    tags: List[str] = Field(default_factory=list)
    layer: str = "long"  # core / long / short / consciousness
    memory_type: str = "fact"  # fact / event / unresolved / date / consciousness
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    timezone: str = "Asia/Shanghai"
    weight: float = 1.0
    valence: float = 0.0  # -1.0 ~ 1.0
    arousal: float = 0.0  # 0.0 ~ 1.0
    pinned: bool = False
    unresolved: bool = False

class MemoryCreate(MemoryBase):
    id: Optional[str] = None
    source_candidate_id: Optional[str] = None
    embedding: Optional[bytes] = None

class MemoryResponse(MemoryBase):
    id: str
    decay_rate: float
    expires_at: Optional[str] = None
    last_triggered_at: Optional[str] = None
    trigger_count: int = 0
    created_at: str
    updated_at: str
    
class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    layer: Optional[str] = None
    memory_type: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    weight: Optional[float] = None
    valence: Optional[float] = None
    arousal: Optional[float] = None
    pinned: Optional[bool] = None
    unresolved: Optional[bool] = None

def generate_id() -> str:
    return f"mem_{uuid.uuid4().hex[:16]}"
