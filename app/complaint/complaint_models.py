from sqlalchemy import Column, BigInteger, Enum, Text, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.common.base_model import BaseModel
import enum


class SubmissionType(enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    TEXT_IMAGE = "TEXT_IMAGE"


class ComplaintStatus(enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


class Complaint(BaseModel):
    __tablename__ = "complaints"

    complaint_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False, index=True)
    submission_type = Column(Enum(SubmissionType), nullable=False)
    original_text = Column(Text, nullable=True)
    processed_text = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    location_details = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.department_id"), nullable=True, index=True)
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.DRAFT, nullable=False, index=True)

    user = relationship("User", back_populates="complaints")
    category = relationship("Category", back_populates="complaints")
    department = relationship("Department", back_populates="complaints")
    files = relationship("File", back_populates="complaint", cascade="all, delete-orphan")
    analyses = relationship("AIAnalysis", back_populates="complaint", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Complaint(id={self.complaint_id}, status='{self.status.value}')>"

    @property
    def is_draft(self) -> bool:
        return self.status == ComplaintStatus.DRAFT

    @property
    def is_submitted(self) -> bool:
        return self.status in [ComplaintStatus.SUBMITTED, ComplaintStatus.PROCESSING, ComplaintStatus.COMPLETED]