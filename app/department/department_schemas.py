from pydantic import BaseModel, ConfigDict
from typing import Optional


class DepartmentBase(BaseModel):
    name: str
    organization: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    category_id: int


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    organization: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    category_id: Optional[int] = None


class DepartmentResponse(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    department_id: int
    category_id: int


class DepartmentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    department_id: int
    name: str
    organization: Optional[str]
    category_id: int