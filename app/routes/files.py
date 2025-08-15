# app/routes/files.py
import os
import uuid
from pathlib import Path
from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from sqlalchemy import select, insert, update, func
from sqlalchemy.orm import Session
from minio import Minio

from app.db import get_db, complaints, files as files_table
from app.auth import get_current_user

# ---- MinIO setup ---------------------------------------------------------
endpoint = os.getenv("MINIO_ENDPOINT")
access   = os.getenv("MINIO_ACCESS_KEY")
secret   = os.getenv("MINIO_SECRET_KEY")
if not endpoint or not access or not secret:
    raise RuntimeError("MINIO_* environment variables are required.")

MINIO_BUCKET = os.getenv("MINIO_BUCKET", "minwon")
_minio = Minio(
    endpoint,
    access_key=access,
    secret_key=secret,
    secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
)

# Ensure bucket exists
if not _minio.bucket_exists(MINIO_BUCKET):
    _minio.make_bucket(MINIO_BUCKET)

router = APIRouter()

# ---- Helpers -------------------------------------------------------------
def _guess_type(ct: str | None) -> str:
    ct = (ct or "").lower()
    if ct.startswith("image/"):
        return "IMAGE"
    if ct == "application/pdf":
        return "PDF"
    return "DOCUMENT"

def _file_length(upload: UploadFile) -> int:
    f = upload.file
    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    return size

def _cleanup_minio_response(resp):
    try:
        resp.close()
    finally:
        try:
            resp.release_conn()
        except Exception:
            pass

# ---- Routes --------------------------------------------------------------
@router.post("/upload", summary="Upload files and attach to a complaint")
def upload_files(
    complaint_id: int = Form(...),
    file_list: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user),
):
    # Verify complaint ownership
    comp = (
        db.execute(select(complaints).where(complaints.c.complaint_id == complaint_id))
        .mappings()
        .first()
    )
    if not comp or comp["user_id"] != user["user_id"]:
        raise HTTPException(404, "Complaint not found")

    outputs = []
    for up in file_list:
        ext = Path(up.filename or "").suffix
        stored = f"{uuid.uuid4().hex}{ext}"
        object_key = f"complaints/{complaint_id}/{stored}"

        length = _file_length(up)
        _minio.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_key,
            data=up.file,
            length=length,
            content_type=up.content_type or "application/octet-stream",
        )

        res = db.execute(
            insert(files_table).values(
                complaint_id=complaint_id,
                original_filename=up.filename or stored,
                stored_filename=stored,
                file_type=_guess_type(up.content_type),
                minio_bucket=MINIO_BUCKET,
                minio_object_key=object_key,
                uploaded_at=func.now(),
            )
        )
        file_id = res.inserted_primary_key[0]
        meta = (
            db.execute(select(files_table).where(files_table.c.file_id == file_id))
            .mappings()
            .first()
        )
        outputs.append(meta)

    # Update submission_type based on presence of text
    new_type = "TEXT_IMAGE" if comp["original_text"] else "IMAGE"
    db.execute(
        update(complaints)
        .where(complaints.c.complaint_id == complaint_id)
        .values(submission_type=new_type, updated_at=func.now())
    )

    db.commit()
    return outputs

@router.get("/{file_id}", summary="Get file metadata")
def get_file_meta(
    file_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user),
):
    f = (
        db.execute(select(files_table).where(files_table.c.file_id == file_id))
        .mappings()
        .first()
    )
    if not f:
        raise HTTPException(404, "File not found")

    comp = (
        db.execute(select(complaints).where(complaints.c.complaint_id == f["complaint_id"]))
        .mappings()
        .first()
    )
    if not comp or comp["user_id"] != user["user_id"]:
        raise HTTPException(404, "File not found")

    return f

@router.get("/{file_id}/download", summary="Download a file from MinIO")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user),
):
    f = (
        db.execute(select(files_table).where(files_table.c.file_id == file_id))
        .mappings()
        .first()
    )
    if not f:
        raise HTTPException(404, "File not found")

    comp = (
        db.execute(select(complaints).where(complaints.c.complaint_id == f["complaint_id"]))
        .mappings()
        .first()
    )
    if not comp or comp["user_id"] != user["user_id"]:
        raise HTTPException(404, "File not found")

    # Stream from MinIO; ensure the response is closed after sending
    resp = _minio.get_object(f["minio_bucket"], f["minio_object_key"])

    media = "application/octet-stream"
    if f["file_type"] == "IMAGE":
        media = "image/*"
    elif f["file_type"] == "PDF":
        media = "application/pdf"

    headers = {
        "Content-Disposition": f'attachment; filename="{f["original_filename"] or f["stored_filename"]}"'
    }

    return StreamingResponse(
        resp.stream(32 * 1024),
        media_type=media,
        headers=headers,
        background=BackgroundTask(_cleanup_minio_response, resp),
    )
