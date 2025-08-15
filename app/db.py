# app/db.py
import os
from typing import Iterator
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Pre-ping to drop dead connections
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Reflect all tables from the current schema
metadata = MetaData()
metadata.reflect(bind=engine)

def get_db() -> Iterator[Session]:
    """Yield a DB session with proper close semantics."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_required_table(name: str) -> Table:
    """Return a reflected Table or raise a clear error if missing."""
    tbl = metadata.tables.get(name)
    if tbl is None:
        raise RuntimeError(f"[DB] Required table not found: {name}")
    return tbl

# Convenience bindings 
complaints: Table   = get_required_table("complaints")
files: Table        = get_required_table("files")
categories: Table   = get_required_table("categories")
departments: Table  = get_required_table("departments")
users: Table        = get_required_table("users")
user_tokens: Table  = get_required_table("user_tokens")
ai_analysis: Table  = get_required_table("ai_analysis")