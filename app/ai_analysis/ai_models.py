from sqlalchemy import Column, BigInteger, Enum, JSON, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class AnalysisType(enum.Enum):
    TEXT_CLASSIFICATION = "TEXT_CLASSIFICATION"
    IMAGE_CLASSIFICATION = "IMAGE_CLASSIFICATION"
    OCR = "OCR"


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    analysis_id = Column(BigInteger, primary_key=True, autoincrement=True)
    complaint_id = Column(BigInteger, ForeignKey("complaints.complaint_id"), nullable=False, index=True)
    analysis_type = Column(Enum(AnalysisType), nullable=False, index=True)
    result = Column(JSON, nullable=False)
    confidence_score = Column(DECIMAL(5, 4), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    complaint = relationship("Complaint", back_populates="analyses")

    def __repr__(self):
        return f"<AIAnalysis(id={self.analysis_id}, type='{self.analysis_type.value}')>"