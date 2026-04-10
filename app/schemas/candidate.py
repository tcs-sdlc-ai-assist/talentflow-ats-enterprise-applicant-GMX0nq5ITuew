from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ApplicationBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    status: str
    created_at: datetime


class CandidateCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    resume_text: Optional[str] = None
    skill_ids: Optional[list[int]] = None

    @field_validator("first_name")
    @classmethod
    def first_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("First name must not be empty")
        if len(v) > 50:
            raise ValueError("First name must be at most 50 characters")
        return v

    @field_validator("last_name")
    @classmethod
    def last_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Last name must not be empty")
        if len(v) > 50:
            raise ValueError("Last name must be at most 50 characters")
        return v

    @field_validator("phone")
    @classmethod
    def phone_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) > 20:
                raise ValueError("Phone must be at most 20 characters")
            if not v:
                return None
        return v

    @field_validator("linkedin_url")
    @classmethod
    def linkedin_url_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) > 255:
                raise ValueError("LinkedIn URL must be at most 255 characters")
            if not v:
                return None
        return v


class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    resume_text: Optional[str] = None
    skill_ids: Optional[list[int]] = None

    @field_validator("first_name")
    @classmethod
    def first_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("First name must not be empty")
            if len(v) > 50:
                raise ValueError("First name must be at most 50 characters")
        return v

    @field_validator("last_name")
    @classmethod
    def last_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Last name must not be empty")
            if len(v) > 50:
                raise ValueError("Last name must be at most 50 characters")
        return v

    @field_validator("phone")
    @classmethod
    def phone_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) > 20:
                raise ValueError("Phone must be at most 20 characters")
            if not v:
                return None
        return v

    @field_validator("linkedin_url")
    @classmethod
    def linkedin_url_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) > 255:
                raise ValueError("LinkedIn URL must be at most 255 characters")
            if not v:
                return None
        return v


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    resume_text: Optional[str] = None
    skills: list[SkillResponse] = []
    applications: list[ApplicationBriefResponse] = []
    created_at: datetime
    updated_at: datetime


class CandidateListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    skills: list[SkillResponse] = []
    created_at: datetime