import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    full_name = Column(String(128), nullable=True)
    role = Column(String(32), nullable=False, default="Interviewer", index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationship: jobs where this user is the hiring manager
    jobs = relationship("Job", back_populates="hiring_manager", lazy="selectin")

    # Relationship: interviews where this user is the interviewer
    interviews = relationship("Interview", back_populates="interviewer", lazy="selectin")

    # Relationship: audit logs created by this user
    audit_logs = relationship("AuditLog", back_populates="user", lazy="selectin")

    # Relationship: offers created by this user
    offers = relationship("Offer", back_populates="created_by_user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"