# app/routes/departments.py
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db, departments
from app.auth import get_current_user

router = APIRouter()

@router.get("", summary="List departments", tags=["Department"])
def list_departments(
    category_id: Optional[int] = Query(None, description="Filter by category_id"),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user),
):
    stmt = select(departments)
    if category_id is not None:
        stmt = stmt.where(departments.c.category_id == category_id)
    rows = db.execute(stmt.order_by(departments.c.department_id)).mappings().all()
    return rows

@router.get("/{department_id}", summary="Get a department by id", tags=["Department"])
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user),
):
    row = (
        db.execute(
            select(departments).where(departments.c.department_id == department_id)
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(404, "Department not found")
    return row
