from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    id: str
    source: str  # "notion" | "gdrive" | ...
    source_id: str
    title: str
    text: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    url: Optional[str] = None
    path: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata_raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    id: str
    document_id: str
    content: str
    metadata: Dict[str, Any]


@dataclass
class RetrievedChunk:
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float

