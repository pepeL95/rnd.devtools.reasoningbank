"""Domain models for the ReasoningBank MVP."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional

Trigger = Literal[
    "user_correction",
    "manual_trigger",
    "learning",
    "failure_analysis",
    "review_feedback",
]
MemoryStatus = Literal["candidate", "active", "rejected", "archived"]
MemoryScope = Literal["local", "global"]
Confidence = Literal["low", "medium", "high"]
DetailLevel = Literal["summary", "body"]

ALLOWED_TRIGGERS = {
    "user_correction",
    "manual_trigger",
    "learning",
    "failure_analysis",
    "review_feedback",
}
ALLOWED_STATUSES = {"candidate", "active", "rejected", "archived"}
ALLOWED_SCOPES = {"local", "global"}


@dataclass
class MemoryRecord:
    id: str
    repo: str
    scope: MemoryScope
    status: MemoryStatus
    markdown_path: str
    name: str
    description: str
    trigger: Trigger
    tags: List[str]
    related_files: List[str]
    evidence_refs: List[str]
    commit_refs: List[str]
    pr_refs: List[str]
    body_hash: str
    embedding_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime]
    created_by: str
    reviewed_by: Optional[str]


@dataclass
class SimilarityEdgeRecord:
    from_memory_id: str
    to_memory_id: str
    score: float
    reasons: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class MemoryInvestigationDecision:
    should_create_memory: bool
    trigger: Optional[Trigger]
    proposed_name: Optional[str]
    proposed_tags: List[str]
    related_files: List[str]
    evidence_refs: List[str]
    commit_refs: List[str]
    rationale: str
    duplicate_of: Optional[str]
    confidence: Confidence


@dataclass
class SynthesizedMemory:
    markdown_path: str
    repo: str
    name: str
    description: str
    trigger: Trigger
    tags: List[str]
    body: str
    related_files: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    commit_refs: List[str] = field(default_factory=list)
    pr_refs: List[str] = field(default_factory=list)
    created_by: str = "runtime-agent"


@dataclass
class RetrievalContext:
    repo: str
    task_text: str
    files_in_scope: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    commit_refs: List[str] = field(default_factory=list)
    pr_refs: List[str] = field(default_factory=list)
    include_candidate_memories: bool = False


@dataclass
class RetrievedMemoryPreview:
    memory_id: str
    name: str
    description: str
    trigger: str
    tags: List[str]
    relevance_score: float
    reasons: List[str]
    activation_hint: str


@dataclass
class MemoryReadRequest:
    memory_id: str
    repo: str
    activation_reason: str
    detail_level: DetailLevel = "body"
    task_id: str = "manual"


@dataclass
class MemoryReadResult:
    memory_id: str
    name: str
    description: str
    tags: List[str]
    body: Optional[str]
    warnings: List[str]


@dataclass
class MemoryActivationEvent:
    memory_id: str
    task_id: str
    repo: str
    activation_reason: str
    activated_at: datetime
    used_in_final_plan: Optional[bool] = None
