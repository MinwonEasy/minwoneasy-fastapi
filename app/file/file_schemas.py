from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.file.file_models import FileType


class FileBase(BaseModel):
    original_filename: str
    file_type: FileType


class FileCreate(FileBase):
    complaint_id: int
    stored_filename: str
    minio_bucket: str
    minio_object_key: str


class FileResponse(FileBase):
    model_config = ConfigDict(from_attributes=True)

    file_id: int
    complaint_id: int
    stored_filename: str
    file_url: str
    uploaded_at: datetime


class FileListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: int
    original_filename: str
    file_type: FileType
    uploaded_at: datetime