# app/config.py
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    BASE_URL: str
    CLIENT_ID: str
    CLIENT_SECRET: str
    REALM: str
    ISSUER_BASE_URL: str
    SESSION_SECRET: str
    DATABASE_URL: str

    class Config:
        env_file = ENV_PATH
        env_file_encoding = "utf-8"


settings = Settings()
