from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.common.base_model import BaseModel


class Category(BaseModel):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)

    departments = relationship("Department", back_populates="category")
    complaints = relationship("Complaint", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.category_id}, name='{self.name}')>"