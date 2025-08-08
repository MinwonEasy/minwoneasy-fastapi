from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class UserTokenBase(BaseModel):
    device_info: Optional[str] = Field(None, max_length=100)
    expires_at: datetime


class UserTokenCreate(UserTokenBase):
    user_id: int = Field(..., gt=0)
    refresh_token_encrypted: str


class UserTokenResponse(UserTokenBase):
    model_config = ConfigDict(from_attributes=True)

    token_id: int
    user_id: int
    is_expired: bool
    created_at: datetime