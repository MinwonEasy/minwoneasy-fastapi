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

# MariaDB 세션 의존성 주입
def get_mariadb() -> Generator[Session, None, None]:
    """MariaDB 세션 반환"""
    db = MariaDBSessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# PostgreSQL 세션 의존성 주입
def get_postgresql() -> Generator[Session, None, None]:
    """PostgreSQL 세션 반환"""
    db = PostgreSQLSessionLocal()
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


