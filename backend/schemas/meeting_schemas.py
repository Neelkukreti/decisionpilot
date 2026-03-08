"""
Pydantic schemas for meeting data structures
Strict validation for all API inputs/outputs
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from enum import Enum


class ExecutionStatus(str, Enum):
    """Execution status enum"""
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DRY_RUN = "dry_run"
    PENDING = "pending"


class QualityScore(BaseModel):
    """Quality scoring metrics"""
    clarity: float = Field(..., ge=0, le=100, description="Clarity score 0-100")
    evidence_quality: float = Field(..., ge=0, le=100, description="Evidence quality 0-100")
    overall: float = Field(..., ge=0, le=100, description="Overall quality 0-100")


class ValidationFeedback(BaseModel):
    """Validation feedback from Critic Agent"""
    item_id: str = Field(..., description="ID of validated item")
    item_type: str = Field(..., description="action|decision")
    quality_score: QualityScore
    issues: List[str] = Field(default_factory=list, description="List of problems found")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    validated_at: str = Field(..., description="ISO timestamp of validation")


class AuditLog(BaseModel):
    """Audit log entry for execution tracking"""
    timestamp: str = Field(..., description="ISO timestamp")
    action_id: str
    action_title: str
    execution_status: str
    ticket_id: Optional[str] = None
    ticket_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class Evidence(BaseModel):
    """Evidence chunk with citation"""
    citation_id: str = Field(..., description="Citation reference like [1]")
    content: str = Field(..., description="Actual evidence text")
    source_type: str = Field(..., description="transcript|slide|whiteboard|screenshot")
    timestamp: Optional[float] = Field(None, description="Timestamp in seconds")
    speaker: Optional[str] = Field(None, description="Speaker name")
    score: Optional[float] = Field(None, description="Relevance score 0-1")


class Decision(BaseModel):
    """Meeting decision with evidence"""
    id: str = Field(..., description="Decision ID like DEC-001")
    title: str = Field(..., min_length=5, description="Decision title")
    description: str = Field(..., min_length=10, description="Full description")
    owner: Optional[str] = Field(None, description="Decision owner")
    rationale: Optional[str] = Field(None, description="Why this decision was made")
    citations: List[str] = Field(default_factory=list, description="Meeting citations")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ActionItem(BaseModel):
    """Action item with quality metrics"""
    id: str = Field(..., description="Action ID like ACT-001")
    title: str = Field(..., min_length=5, description="Action title")
    description: str = Field(..., min_length=10, description="Full description")
    owner: Optional[str] = Field(None, description="Person responsible")
    deadline: Optional[date] = Field(None, description="Due date")
    priority: str = Field(default="medium", pattern=r"^(high|medium|low)$")
    citations: List[str] = Field(default_factory=list, description="Meeting citations")
    clarity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    evidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    execution_risk: str = Field(default="medium", pattern=r"^(low|medium|high)$")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class Risk(BaseModel):
    """Identified risk with mitigation"""
    risk_id: str = Field(..., pattern=r"^RISK-\d{3}$")
    description: str = Field(..., min_length=10)
    severity: str = Field(..., pattern=r"^(critical|high|medium|low)$")
    mitigation: Optional[str]
    owner: Optional[str]
    citations: List[str] = Field(..., min_items=1)
    confidence: float = Field(..., ge=0.0, le=1.0)


class OpenQuestion(BaseModel):
    """Unresolved question from meeting"""
    question_id: str = Field(..., pattern=r"^Q-\d{3}$")
    question: str = Field(..., min_length=5)
    asker: str
    requires_followup: bool
    citations: List[str] = Field(..., min_items=1)


class MeetingAnalysis(BaseModel):
    """Complete meeting analysis output"""
    meeting_id: str
    summary: str = Field(..., min_length=50)
    decisions: List[Decision]
    action_items: List[ActionItem]
    risks: List[Risk]
    open_questions: List[OpenQuestion]
    extraction_timestamp: datetime
    evidence_references: List[Evidence]


class ExecutionResult(BaseModel):
    """Result of executing a single action"""
    action_id: str
    status: ExecutionStatus
    ticket_id: Optional[str] = None
    ticket_url: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    retry_count: int = Field(default=0, ge=0)
    screenshot_b64: Optional[str] = None


class ExecutionReport(BaseModel):
    """Summary of batch execution"""
    meeting_id: str
    execution_timestamp: datetime
    total_actions: int
    successful: int
    failed: int
    execution_results: List[ExecutionResult]
    total_execution_time_ms: float
    avg_retry_count: float


class MeetingUploadRequest(BaseModel):
    """Request to process a new meeting"""
    meeting_title: str = Field(..., min_length=3)
    meeting_date: Optional[datetime] = None
    participants: List[str] = Field(default_factory=list)


class MeetingUploadResponse(BaseModel):
    """Response after uploading meeting"""
    meeting_id: str
    status: str
    message: str
