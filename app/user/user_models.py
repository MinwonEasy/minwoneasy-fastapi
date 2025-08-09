from sqlalchemy import Column, String, DateTime, BigInteger
from sqlalchemy.orm import relationship
from database.mariadb_connection import MariaDBBase


class User(MariaDBBase):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    keycloak_user_id = Column(String(36), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    family_name = Column(String(50), nullable=False)
    given_name = Column(String(50), nullable=False)
    display_name = Column(String(50), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    complaints = relationship("Complaint", back_populates="user", lazy="select")
    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return f"{self.family_name}{self.given_name}"

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None