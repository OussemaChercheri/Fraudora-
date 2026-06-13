from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql://fraudguard:password@127.0.0.1:5433/fraudguard_db"
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    OCR_LANG: str = "fra+eng"
    ENV: str = "production"

    SMTP_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@fraudguard.tn"
    DAILY_EMAIL_HOUR: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
