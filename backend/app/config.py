from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "绿风环境花卉 ERP"
    app_secret: str = "dev-only-change-before-production"
    database_url: str = "sqlite:///./greenwind.db"
    frontend_origin: str = "http://127.0.0.1:5173"
    frontend_origins: str = ""
    frontend_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|192\.168\.\d+\.\d+|175\.178\.106\.253)(:5173)?$"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
