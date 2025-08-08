from sqlalchemy import Column, BigInteger, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class FileType(enum.Enum):
    IMAGE = "IMAGE"
    PDF = "PDF"
    DOCUMENT = "DOCUMENT"


class File(Base):
    __tablename__ = "files"

    file_id = Column(BigInteger, primary_key=True, autoincrement=True)
    complaint_id = Column(BigInteger, ForeignKey("complaints.complaint_id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_type = Column(Enum(FileType), nullable=False)
    minio_bucket = Column(String(100), nullable=False)
    minio_object_key = Column(String(500), nullable=False, unique=True)
    uploaded_at = Column(DateTime, default=func.now(), nullable=False)

    complaint = relationship("Complaint", back_populates="files")

    def __repr__(self):
        return f"<File(id={self.file_id}, filename='{self.original_filename}')>"

    @property
    def file_url(self) -> str:
        return f"http://34.22.78.216:31112/{self.minio_bucket}/{self.minio_object_key}"