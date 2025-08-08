from sqlalchemy import Column, BigInteger, Text, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from app.common.base_model import BaseModel


class UserToken(BaseModel):
    __tablename__ = "user_tokens"

    token_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False, index=True)
    refresh_token_encrypted = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    device_info = Column(String(100), nullable=True)

    user = relationship("User", back_populates="tokens")

    def __repr__(self):
        return f"<UserToken(id={self.token_id}, user_id={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        from datetime import datetime
        return self.expires_at < datetime.now()
