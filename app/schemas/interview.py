from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class InterviewCreate(BaseModel):
    application_id: int
    interviewer_id: int
    scheduled_at: datetime

    @field_validator("application_id", "interviewer_id")
    @classmethod
    def validate_positive_id(cls, v: int, info) -> int:
        if v <= 0:
            raise ValueError(f"{info.field_name} must be a positive integer")
        return v


class InterviewFeedback(BaseModel):
    feedback_rating: int
    feedback_notes: Optional[str] = None

    @field_validator("feedback_rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("feedback_rating must be between 1 and 5")
        return v

    @field_validator("feedback_notes")
    @classmethod
    def validate_feedback_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    interviewer_id: int
    scheduled_at: datetime
    feedback_rating: Optional[int] = None
    feedback_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime