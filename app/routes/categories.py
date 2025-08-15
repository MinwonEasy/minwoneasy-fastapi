# app/routes/categories.py
from typing import Dict
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db, categories
from app.auth import get_current_user

router = APIRouter()

@router.get("", summary="List complaint categories", tags=["Category"])
def list_categories(
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user),
):
    rows = (
        db.execute(select(categories).order_by(categories.c.category_id))
        .mappings()
        .all()
    )
    return rows
