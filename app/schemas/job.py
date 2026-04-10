from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class JobBase(BaseModel):
    title: str
    department: str
    location: str
    type: str
    salary_min: int
    salary_max: int
    description: str
    hiring_manager_id: int

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title must not be empty")
        if len(v) > 100:
            raise ValueError("Title must be at most 100 characters")
        return v

    @field_validator("department")
    @classmethod
    def department_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Department must not be empty")
        if len(v) > 50:
            raise ValueError("Department must be at most 50 characters")
        return v

    @field_validator("location")
    @classmethod
    def location_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Location must not be empty")
        if len(v) > 100:
            raise ValueError("Location must be at most 100 characters")
        return v

    @field_validator("type")
    @classmethod
    def type_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Type must not be empty")
        if len(v) > 30:
            raise ValueError("Type must be at most 30 characters")
        return v

    @field_validator("salary_min")
    @classmethod
    def salary_min_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Salary min must be a positive number")
        return v

    @field_validator("salary_max")
    @classmethod
    def salary_max_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Salary max must be a positive number")
        return v

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description must not be empty")
        return v

    @field_validator("hiring_manager_id")
    @classmethod
    def hiring_manager_id_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Hiring manager ID must be a positive integer")
        return v

    @field_validator("salary_max")
    @classmethod
    def salary_max_gte_min(cls, v: int, info: object) -> int:
        data = info.data if hasattr(info, "data") else {}
        salary_min = data.get("salary_min")
        if salary_min is not None and v < salary_min:
            raise ValueError("Salary max must be greater than or equal to salary min")
        return v


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    hiring_manager_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title must not be empty")
            if len(v) > 100:
                raise ValueError("Title must be at most 100 characters")
        return v

    @field_validator("department")
    @classmethod
    def department_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Department must not be empty")
            if len(v) > 50:
                raise ValueError("Department must be at most 50 characters")
        return v

    @field_validator("location")
    @classmethod
    def location_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Location must not be empty")
            if len(v) > 100:
                raise ValueError("Location must be at most 100 characters")
        return v

    @field_validator("type")
    @classmethod
    def type_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Type must not be empty")
            if len(v) > 30:
                raise ValueError("Type must be at most 30 characters")
        return v

    @field_validator("salary_min")
    @classmethod
    def salary_min_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Salary min must be a positive number")
        return v

    @field_validator("salary_max")
    @classmethod
    def salary_max_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Salary max must be a positive number")
        return v

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Description must not be empty")
        return v

    @field_validator("hiring_manager_id")
    @classmethod
    def hiring_manager_id_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Hiring manager ID must be a positive integer")
        return v

    @field_validator("salary_max")
    @classmethod
    def salary_max_gte_min(cls, v: Optional[int], info: object) -> Optional[int]:
        if v is not None:
            data = info.data if hasattr(info, "data") else {}
            salary_min = data.get("salary_min")
            if salary_min is not None and v < salary_min:
                raise ValueError("Salary max must be greater than or equal to salary min")
        return v


class JobStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        v = v.strip()
        allowed = {"Draft", "Published", "Closed"}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(sorted(allowed))}")
        return v


class HiringManagerBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    department: str
    location: str
    type: str
    salary_min: int
    salary_max: int
    description: str
    status: str
    hiring_manager_id: int
    hiring_manager: Optional[HiringManagerBrief] = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    department: str
    location: str
    type: str
    status: str
    hiring_manager_id: int
    hiring_manager: Optional[HiringManagerBrief] = None
    created_at: datetime
    updated_at: datetime