from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    email: str
    family_name: str
    given_name: str


class UserCreate(UserBase):
    keycloak_user_id: str


class UserUpdate(BaseModel):
    family_name: Optional[str] = None
    given_name: Optional[str] = None
    display_name: Optional[str] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    keycloak_user_id: str
    display_name: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    display_name: str
    full_name: str
    created_at: datetime