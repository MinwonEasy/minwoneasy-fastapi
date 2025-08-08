from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func
from database.mariadb_connection import MariaDBBase


class BaseModel(MariaDBBase):
    __abstract__ = True

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)