from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class AuditLogCreate(BaseModel):
    action: str
    entity_type: str
    entity_id: int
    details: Optional[str] = None
    user_id: int

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed_actions = [
            "Job Published",
            "Job Closed",
            "Job Created",
            "Job Updated",
            "Job Archived",
            "Candidate Created",
            "Candidate Updated",
            "Candidate Rejected",
            "Candidate Hired",
            "Application Created",
            "Application Updated",
            "Application Status Changed",
            "Interview Scheduled",
            "Interview Completed",
            "Interview Cancelled",
            "Feedback Submitted",
            "User Created",
            "User Updated",
            "User Deactivated",
        ]
        if v not in allowed_actions:
            raise ValueError(f"Invalid action: {v}. Must be one of: {allowed_actions}")
        return v

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        allowed_entity_types = [
            "Job",
            "Candidate",
            "Application",
            "Interview",
            "Feedback",
            "User",
        ]
        if v not in allowed_entity_types:
            raise ValueError(
                f"Invalid entity_type: {v}. Must be one of: {allowed_entity_types}"
            )
        return v

    @field_validator("entity_id")
    @classmethod
    def validate_entity_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError("entity_id must be a positive integer")
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError("user_id must be a positive integer")
        return v


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity_type: str
    entity_id: int
    details: Optional[str] = None
    user_id: int
    timestamp: datetime


class AuditLogListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_logs: list[AuditLogResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class AuditLogFilter(BaseModel):
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    user_id: Optional[int] = None
    page: int = 1
    per_page: int = 20

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page must be >= 1")
        return v

    @field_validator("per_page")
    @classmethod
    def validate_per_page(cls, v: int) -> int:
        if v < 10 or v > 100:
            raise ValueError("per_page must be between 10 and 100")
        return v