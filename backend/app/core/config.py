from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):

    PROJECT_NAME: str = "WorkScout"
    VERSION: str = "1.0.0"

    #В продакшене надо выключить
    DEBUG: bool = True

    # ========== БЕЗОПАСНОСТЬ ==========

    SECRET_KEY: str = "change-me-in-production"

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ========== БАЗА ДАННЫХ ==========

   
    DATABASE_URL: str = "postgresql+asyncpg://workscout:workscout@localhost:5432/workscout"

    # ========== REDIS ==========

    REDIS_URL: str = "redis://localhost:6379"

    # ========== CORS ==========

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True
        
settings = Settings()
