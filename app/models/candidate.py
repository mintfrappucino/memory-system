from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CandidateBase(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    proposed_memory_type: Optional[str] = "fact"
    proposed_layer: Optional[str] = "long"
    proposed_event_date: Optional[str] = None
    proposed_valence: float = 0.5
    proposed_arousal: float = 0.0
    proposed_unresolved: bool = False
    confidence: float = 0.5
    status: str = "pending"  # pending / accepted / rejected

class CandidateResponse(CandidateBase):
    id: str
    created_at: str
