# app/routes/complaints.py
from typing import Optional, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.orm import Session

from app.db import get_db, complaints, files as files_table, categories, departments
from app.auth import get_current_user

router = APIRouter()

# ---------- Request Schemas ----------
class ComplaintCreate(BaseModel):
    input_text: Optional[str] = None
    location: Optional[str] = None
    location_details: Optional[str] = None
    category_id: Optional[int] = None
    department_id: Optional[int] = None
    # Must be one of: DRAFT | SUBMITTED | PROCESSING | COMPLETED
    status: Optional[str] = "SUBMITTED"

class ComplaintUpdate(BaseModel):
    input_text: Optional[str] = None
    processed_text: Optional[str] = None
    location: Optional[str] = None
    location_details: Optional[str] = None
    category_id: Optional[int] = None
    department_id: Optional[int] = None
    # Must be one of: DRAFT | SUBMITTED | PROCESSING | COMPLETED
    status: Optional[str] = None

# ---------- Routes ----------
@router.post("/create", summary="Create a new complaint")
def create_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # Validate optional foreign keys
    if payload.category_id is not None:
        exists = db.scalar(
            select(categories.c.category_id).where(categories.c.category_id == payload.category_id)
        )
        if not exists:
            raise HTTPException(400, "Invalid category_id")

    if payload.department_id is not None:
        exists = db.scalar(
            select(departments.c.department_id).where(departments.c.department_id == payload.department_id)
        )
        if not exists:
            raise HTTPException(400, "Invalid department_id")

    # Decide submission type by presence of text (files -> handled in file upload route)
    submission_type = "TEXT" if payload.input_text else "IMAGE"

    res = db.execute(
        insert(complaints).values(
            user_id=user["user_id"],
            submission_type=submission_type,
            original_text=payload.input_text,
            processed_text=None,
            location=payload.location,
            location_details=payload.location_details,
            category_id=payload.category_id,
            department_id=payload.department_id,
            status=payload.status or "SUBMITTED",
            created_at=func.now(),
            updated_at=func.now(),
        )
    )
    db.commit()
    return _get(db, res.inserted_primary_key[0], user["user_id"])

@router.get("/list", summary="List complaints for the current user")
def list_my_complaints(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rows = (
        db.execute(
            select(complaints)
            .where(complaints.c.user_id == user["user_id"])
            .order_by(complaints.c.created_at.desc())
        )
        .mappings()
        .all()
    )
    return [_with_files(db, r) for r in rows]

@router.get("/{complaint_id}", summary="Get complaint details")
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return _get(db, complaint_id, user["user_id"])

@router.put("/{complaint_id}", summary="Update a complaint")
def update_complaint(
    complaint_id: int,
    payload: ComplaintUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    row = (
        db.execute(select(complaints).where(complaints.c.complaint_id == complaint_id))
        .mappings()
        .first()
    )
    if not row or row["user_id"] != user["user_id"]:
        raise HTTPException(404, "Complaint not found")

    # Validate optional foreign keys
    if payload.category_id is not None:
        exists = db.scalar(
            select(categories.c.category_id).where(categories.c.category_id == payload.category_id)
        )
        if not exists:
            raise HTTPException(400, "Invalid category_id")

    if payload.department_id is not None:
        exists = db.scalar(
            select(departments.c.department_id).where(departments.c.department_id == payload.department_id)
        )
        if not exists:
            raise HTTPException(400, "Invalid department_id")

    # Build update payload
    values: dict[str, Any] = {"updated_at": func.now()}
    if payload.input_text is not None:
        values["original_text"] = payload.input_text
    if payload.processed_text is not None:
        values["processed_text"] = payload.processed_text
    if payload.location is not None:
        values["location"] = payload.location
    if payload.location_details is not None:
        values["location_details"] = payload.location_details
    if payload.category_id is not None:
        values["category_id"] = payload.category_id
    if payload.department_id is not None:
        values["department_id"] = payload.department_id
    if payload.status is not None:
        values["status"] = payload.status

    # If text changed, re-evaluate submission type with file existence
    if "original_text" in values:
        has_file = (
            db.scalar(
                select(func.count())
                .select_from(files_table)
                .where(files_table.c.complaint_id == complaint_id)
            )
            > 0
        )
        values["submission_type"] = "TEXT_IMAGE" if has_file else "TEXT"

    db.execute(
        update(complaints)
        .where(complaints.c.complaint_id == complaint_id)
        .values(**values)
    )
    db.commit()
    return _get(db, complaint_id, user["user_id"])

@router.delete("/{complaint_id}", status_code=204, summary="Delete a complaint")
def delete_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    row = (
        db.execute(select(complaints).where(complaints.c.complaint_id == complaint_id))
        .mappings()
        .first()
    )
    if not row or row["user_id"] != user["user_id"]:
        raise HTTPException(404, "Complaint not found")

    db.execute(delete(complaints).where(complaints.c.complaint_id == complaint_id))
    db.commit()

# ---------- Internal helpers ----------
def _with_files(db: Session, row: dict) -> dict:
    """Attach file list to a complaint row."""
    fs = (
        db.execute(
            select(files_table)
            .where(files_table.c.complaint_id == row["complaint_id"])
            .order_by(files_table.c.uploaded_at.desc())
        )
        .mappings()
        .all()
    )
    d = dict(row)
    d["files"] = fs
    return d

def _get(db: Session, complaint_id: int, user_id: int) -> dict:
    """Fetch a single complaint by id for the given user and attach files."""
    r = (
        db.execute(select(complaints).where(complaints.c.complaint_id == complaint_id))
        .mappings()
        .first()
    )
    if not r or r["user_id"] != user_id:
        raise HTTPException(404, "Complaint not found")
    return _with_files(db, r)
