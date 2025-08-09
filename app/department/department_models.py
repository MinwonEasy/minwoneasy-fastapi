from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database.mariadb_connection import MariaDBBase


class Department(MariaDBBase):
    __tablename__ = "departments"

    department_id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    organization = Column(String(100), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(100), nullable=True)

    category = relationship("Category", back_populates="departments")
    complaints = relationship("Complaint", back_populates="department")

    def __repr__(self):
        return f"<Department(id={self.department_id}, name='{self.name}')>"