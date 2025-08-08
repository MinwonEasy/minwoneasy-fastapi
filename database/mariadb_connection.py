from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

MARIADB_USER = os.getenv("MARIADB_USER")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD")
MARIADB_HOST = os.getenv("MARIADB_HOST")
MARIADB_PORT = os.getenv("MARIADB_PORT")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE")

MARIADB_URL = f'mysql+pymysql://{MARIADB_USER}:{MARIADB_PASSWORD}@{MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DATABASE}?charset=utf8mb4'

mariadb_engine = create_engine(MARIADB_URL, echo=True)
MariaDBSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mariadb_engine)
MariaDBBase = declarative_base()

