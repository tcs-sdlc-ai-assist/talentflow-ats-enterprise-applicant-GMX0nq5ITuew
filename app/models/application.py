from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


ALLOWED_TRANSITIONS = {
    "Applied": ["Screening", "Rejected"],
    "Screening": ["Interview", "Rejected"],
    "Interview": ["Offer", "Rejected"],
    "Offer": ["Hired", "Rejected"],
    "Hired": [],
    "Rejected": [],
}

ALLOWED_STATUSES = ["Applied", "Screening", "Interview", "Offer", "Hired", "Rejected"]


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(15), nullable=False, default="Applied")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job"),
    )

    job = relationship("Job", back_populates="applications", lazy="selectin")
    candidate = relationship("Candidate", back_populates="applications", lazy="selectin")
    interviews = relationship(
        "Interview",
        back_populates="application",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    offers = relationship(
        "Offer",
        back_populates="application",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Application(id={self.id}, job_id={self.job_id}, "
            f"candidate_id={self.candidate_id}, status='{self.status}')>"
        )