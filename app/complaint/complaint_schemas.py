from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.complaint.complaint_models import SubmissionType, ComplaintStatus


class ComplaintBase(BaseModel):
    submission_type: SubmissionType
    original_text: Optional[str] = None
    location: Optional[str] = None
    location_details: Optional[str] = None


class ComplaintCreate(ComplaintBase):
    category_id: Optional[int] = None
    status: ComplaintStatus = ComplaintStatus.DRAFT


class ComplaintUpdate(BaseModel):
    original_text: Optional[str] = None
    location: Optional[str] = None
    location_details: Optional[str] = None
    category_id: Optional[int] = None
    department_id: Optional[int] = None
    status: Optional[ComplaintStatus] = None


class ComplaintResponse(ComplaintBase):
    model_config = ConfigDict(from_attributes=True)

    complaint_id: int
    user_id: int
    processed_text: Optional[str]
    category_id: Optional[int]
    department_id: Optional[int]
    status: ComplaintStatus
    is_draft: bool
    is_submitted: bool
    created_at: datetime
    updated_at: datetime


class ComplaintListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    complaint_id: int
    submission_type: SubmissionType
    original_text: Optional[str]
    location: Optional[str]
    status: ComplaintStatus
    created_at: datetime
