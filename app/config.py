from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pathlib import Path
from cryptography.fernet import Fernet

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
    DATABASE_URL: str = ""
    MARIADB_USER: str
    MARIADB_PASSWORD: str
    MARIADB_HOST: str
    MARIADB_PORT: str
    MARIADB_DATABASE: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DATABASE: str
    MINIO_ENDPOINT: str
    MINIO_SECURE: bool = False
    TOKEN_ENCRYPTION_KEY: str = ""

    class Config:
        env_file = ENV_PATH
        env_file_encoding = "utf-8"

    @property
    def minio_url(self) -> str:
        protocol = "https" if self.MINIO_SECURE else "http"
        return f"{protocol}://{self.MINIO_ENDPOINT}"

    @property
    def mariadb_url(self) -> str:
        return f'mysql+pymysql://{self.MARIADB_USER}:{self.MARIADB_PASSWORD}@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}?charset=utf8mb4'

    @property
    def encryption_key(self) -> bytes:
        if not self.TOKEN_ENCRYPTION_KEY:
            raise ValueError("TOKEN_ENCRYPTION_KEY must be set in environment variables")
        return self.TOKEN_ENCRYPTION_KEY.encode()


settings = Settings()