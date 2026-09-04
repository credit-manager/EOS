"""
إعدادات التطبيق الرئيسية
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """إعدادات النظام"""
    
    # إعدادات التطبيق
    APP_NAME: str = "نظام ERP المتكامل"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    
    # إعدادات قاعدة البيانات
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/erp_db"
    DATABASE_ASYNC_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/erp_db"
    
    # إعدادات Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # إعدادات الأمان
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # إعدادات CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ]
    
    # إعدادات البريد الإلكتروني
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str | None = None
    
    # إعدادات الملفات
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # إعدادات اللغة
    DEFAULT_LANGUAGE: str = "ar"
    SUPPORTED_LANGUAGES: list = ["ar", "en"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
