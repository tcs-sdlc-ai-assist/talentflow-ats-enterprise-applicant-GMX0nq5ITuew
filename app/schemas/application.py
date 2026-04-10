from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


ALLOWED_STATUSES = ["Applied", "Screening", "Interview", "Offer", "Hired", "Rejected"]

ALLOWED_TRANSITIONS = {
    "Applied": ["Screening", "Rejected"],
    "Screening": ["Interview", "Rejected"],
    "Interview": ["Offer", "Rejected"],
    "Offer": ["Hired", "Rejected"],
    "Hired": [],
    "Rejected": [],
}


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    job_id: int
    candidate_id: int

    @field_validator("job_id")
    @classmethod
    def job_id_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("job_id must be a positive integer")
        return v

    @field_validator("candidate_id")
    @classmethod
    def candidate_id_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("candidate_id must be a positive integer")
        return v


class ApplicationStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in ALLOWED_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(ALLOWED_STATUSES)}"
            )
        return v


class CandidateBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str


class JobBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    department: str
    status: str


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    job_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    candidate: Optional[CandidateBrief] = None
    job: Optional[JobBrief] = None


class ApplicationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ApplicationResponse]
    total: int


class KanbanColumn(BaseModel):
    status: str
    applications: list[ApplicationResponse]


class KanbanResponse(BaseModel):
    job_id: int
    columns: list[KanbanColumn]