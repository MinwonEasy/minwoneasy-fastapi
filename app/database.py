from typing import Generator
from sqlalchemy.orm import Session

from database.mariadb_connection import (
    mariadb_engine,
    MariaDBSessionLocal,
    MariaDBBase
)
from database.postgresql_connection import (
    PostgreSQLSessionLocal,
)
Base = MariaDBBase
engine = mariadb_engine
SessionLocal = MariaDBSessionLocal
from app.user.user_models import User
from app.category.category_models import Category
from app.department.department_models import Department
from app.complaint.complaint_models import Complaint
from app.file.file_models import File
from app.ai_analysis.ai_models import AIAnalysis
from app.user_token.token_models import UserToken

def get_mariadb() -> Generator[Session, None, None]:
    db = MariaDBSessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()



def get_db() -> Generator[Session, None, None]:
    return get_mariadb()


def create_mariadb_tables():
    print("🗄️  Creating MariaDB tables...")
    MariaDBBase.metadata.create_all(bind=mariadb_engine)
    print("✅ MariaDB tables created successfully!")



def create_all_tables():
    create_mariadb_tables()


def drop_mariadb_tables():
    print("⚠️  Dropping MariaDB tables...")
    MariaDBBase.metadata.drop_all(bind=mariadb_engine)
    print("🗑️  MariaDB tables dropped!")


