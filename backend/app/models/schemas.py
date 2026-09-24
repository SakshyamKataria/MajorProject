from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID


# --- Enums / Constants ---
class MeetingStatus:
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionItemPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionItemStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# --- Profile Models ---
class ProfileBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class Profile(ProfileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


# --- Meeting Models ---
class MeetingBase(BaseModel):
    title: str = "Untitled Meeting"
    description: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: int = 0
    status: str = MeetingStatus.PENDING
    error_message: Optional[str] = None
    speaker_names: Dict[str, str] = Field(default_factory=dict)


class MeetingCreate(MeetingBase):
    user_id: UUID


class Meeting(MeetingBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


# --- Participant Models ---
class ParticipantBase(BaseModel):
    name: str
    email: Optional[str] = None
    speaker_label: Optional[str] = None


class Participant(ParticipantBase):
    id: UUID
    meeting_id: UUID
    created_at: datetime


# --- Transcript Models (with classifier tags) ---
class TranscriptBase(BaseModel):
    speaker: Optional[str] = None
    speaker_label: Optional[str] = None
    sentence_order: int
    start_time: float = 0.0
    end_time: float = 0.0
    text: str
    classifier_label: Optional[str] = None
    classifier_confidence: Optional[float] = None


class Transcript(TranscriptBase):
    id: UUID
    meeting_id: UUID
    created_at: datetime


# --- Summary Models ---
class SummaryBase(BaseModel):
    executive_summary: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)
    raw_ai_response: Optional[dict[str, Any]] = None


class Summary(SummaryBase):
    id: UUID
    meeting_id: UUID
    created_at: datetime


# --- Decision Models ---
class DecisionBase(BaseModel):
    decision: str
    context: Optional[str] = None
    decided_by: Optional[str] = None


class Decision(DecisionBase):
    id: UUID
    meeting_id: UUID
    created_at: datetime


# --- Action Item Models ---
class ActionItemBase(BaseModel):
    task: str
    assignee: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: str = ActionItemPriority.MEDIUM
    status: str = ActionItemStatus.PENDING
    tags: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None


class ActionItem(ActionItemBase):
    id: UUID
    meeting_id: UUID
    created_at: datetime
    updated_at: datetime


# --- Meeting Tag Models ---
class MeetingTagBase(BaseModel):
    tag: str


class MeetingTag(MeetingTagBase):
    id: UUID
    meeting_id: UUID
    created_at: datetime


# --- Embedding Models ---
class EmbeddingBase(BaseModel):
    chunk_type: str
    content: str
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)
    embedding: List[float]


class Embedding(EmbeddingBase):
    id: UUID
    meeting_id: UUID
    created_at: datetime


# --- Speaker Customization Models ---
class SpeakerStats(BaseModel):
    speaker_label: str
    display_name: str
    custom_name: Optional[str] = None
    segment_count: int = 0
    total_talk_time_seconds: float = 0.0
    percentage: float = 0.0
    sample_quote: Optional[str] = None


class MeetingSpeakersResponse(BaseModel):
    meeting_id: UUID
    speakers: List[SpeakerStats] = Field(default_factory=list)


class UpdateSpeakersRequest(BaseModel):
    speakers: Dict[str, str] = Field(default_factory=dict)

