# app/routes/__init__.py
from .complaints import router as complaints_router
from .files import router as files_router
from .categories import router as categories_router
from .departments import router as departments_router

__all__ = ["complaints_router", "files_router", "categories_router", "departments_router"]