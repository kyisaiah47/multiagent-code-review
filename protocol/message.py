from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class AgentRole(str, Enum):
    security = "security"
    performance = "performance"
    static = "static"
    test_coverage = "test_coverage"
    documentation = "documentation"
    moderator = "moderator"


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    file: str
    line: Optional[int] = None
    line_end: Optional[int] = None
    severity: Severity
    category: AgentRole
    title: str
    description: str
    suggestion: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str


class DebateStance(str, Enum):
    agree = "agree"
    maintain = "maintain"
    concede_partial = "concede_partial"


class DebateMessage(BaseModel):
    round: int
    agent: AgentRole
    target_finding_id: str
    challenger_finding_id: str
    stance: DebateStance
    reasoning: str
    updated_confidence: float = Field(ge=0.0, le=1.0)


class Conflict(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    finding_a: Finding
    finding_b: Finding
    conflict_type: str  # "location" | "semantic"
    description: str


class ConsensusResult(BaseModel):
    finding: Finding
    consensus_reached: bool
    agreement_score: float
    supporting_agents: list[AgentRole]
    debate_transcript: list[DebateMessage]
    resolution: str
    requires_human_review: bool


class ReviewResult(BaseModel):
    filename: str
    total_findings: int
    consensus_findings: list[ConsensusResult]
    unresolved_conflicts: list[Conflict]
    metrics: ReviewMetrics


class ReviewMetrics(BaseModel):
    agents_used: int
    debate_rounds: int
    conflicts_detected: int
    conflicts_resolved: int
    high_confidence_findings: int
    requires_human_review: int
